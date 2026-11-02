"""Business rules: eligibility, status flow, interview rules, cascading deletes."""
from datetime import date

import store
from errors import ApiError, ConflictError, NotFoundError

# Which status changes are allowed from each status
STATUS_FLOW = {
    "Applied": {"Shortlisted", "Rejected"},
    "Shortlisted": {"Interview Scheduled", "Selected", "Rejected"},
    "Interview Scheduled": {"Shortlisted", "Selected", "Rejected"},
    "Selected": {"Rejected"},
    "Rejected": {"Shortlisted"},
}


# ---------- lookups ----------
def get_student_or_404(student_id):
    s = store.students.get(student_id)
    if not s:
        raise NotFoundError("Student")
    return s


def get_job_or_404(job_id):
    j = store.jobs.get(job_id)
    if not j:
        raise NotFoundError("Job")
    return j


def get_application_or_404(app_id):
    a = store.applications.get(app_id)
    if not a:
        raise NotFoundError("Application")
    return a


def get_interview_or_404(iv_id):
    i = store.interviews.get(iv_id)
    if not i:
        raise NotFoundError("Interview")
    return i


# ---------- eligibility ----------
def check_eligibility(student, job):
    dept_ok = student["department"] in job["departments"]
    cgpa_ok = student["cgpa"] >= job["minCgpa"]
    back_ok = student["backlogs"] <= job["maxBacklogs"]
    open_ok = job["status"] == "Open" and job["deadline"] >= date.today().isoformat()
    if open_ok:
        open_detail = f"Open until {job['deadline']}"
    else:
        open_detail = "Job is closed" if job["status"] != "Open" else "Deadline has passed"
    checks = [
        {"label": "Department", "ok": dept_ok,
         "detail": f"{student['department']} {'is allowed' if dept_ok else 'is not allowed'} "
                   f"(needs {', '.join(job['departments'])})"},
        {"label": "CGPA", "ok": cgpa_ok,
         "detail": f"Student {student['cgpa']:.2f} vs required {job['minCgpa']}"},
        {"label": "Backlogs", "ok": back_ok,
         "detail": f"Student {student['backlogs']} vs maximum {job['maxBacklogs']}"},
        {"label": "Job open", "ok": open_ok, "detail": open_detail},
    ]
    return {"eligible": all(c["ok"] for c in checks), "checks": checks}


# ---------- students ----------
def _check_student_unique(clean, ignore_id=None):
    problems = {}
    for s in store.students.all():
        if s["id"] == ignore_id:
            continue
        if s["rollNo"] == clean["rollNo"]:
            problems["rollNo"] = "Roll number already exists"
        if s["email"] == clean["email"]:
            problems["email"] = "Email already exists"
    if problems:
        raise ConflictError("Student already exists", problems)


def create_student(clean):
    _check_student_unique(clean)
    return store.students.insert(clean)


def update_student(student_id, clean):
    get_student_or_404(student_id)
    _check_student_unique(clean, ignore_id=student_id)
    return store.students.update(student_id, clean)


def sync_placed(student_id):
    """A student is 'placed' when at least one application is Selected."""
    if store.students.get(student_id):
        placed = any(a["studentId"] == student_id and a["status"] == "Selected"
                     for a in store.applications.all())
        store.students.update(student_id, {"placed": placed})


def delete_student(student_id):
    get_student_or_404(student_id)
    for a in store.applications.all():
        if a["studentId"] == student_id:
            delete_application(a["id"], sync=False)
    store.students.delete(student_id)


# ---------- jobs ----------
def delete_job(job_id):
    get_job_or_404(job_id)
    affected = set()
    for a in store.applications.all():
        if a["jobId"] == job_id:
            affected.add(a["studentId"])
            delete_application(a["id"], sync=False)
    store.jobs.delete(job_id)
    for sid in affected:
        sync_placed(sid)


# ---------- applications ----------
def create_application(student_id, job_id):
    student = get_student_or_404(student_id)
    job = get_job_or_404(job_id)
    for a in store.applications.all():
        if a["studentId"] == student_id and a["jobId"] == job_id:
            raise ConflictError("This student has already applied for this job")
    result = check_eligibility(student, job)
    if not result["eligible"]:
        reasons = "; ".join(f"{c['label']}: {c['detail']}" for c in result["checks"] if not c["ok"])
        raise ApiError(f"Student is not eligible for this job. {reasons}", 422)
    return store.applications.insert({
        "studentId": student_id, "jobId": job_id,
        "appliedOn": date.today().isoformat(), "status": "Applied",
    })


def change_application_status(app_id, new_status):
    app = get_application_or_404(app_id)
    old = app["status"]
    if new_status == old:
        raise ConflictError(f"Status is already '{old}'")
    if new_status not in STATUS_FLOW[old]:
        allowed = ", ".join(sorted(STATUS_FLOW[old]))
        raise ApiError(f"Cannot change status from '{old}' to '{new_status}'. Allowed: {allowed}", 422)
    if new_status == "Interview Scheduled" and not any(
            i["applicationId"] == app_id for i in store.interviews.all()):
        raise ConflictError("Schedule the interview first (Interview Schedule page)")
    updated = store.applications.update(app_id, {"status": new_status})
    sync_placed(app["studentId"])
    return updated


def delete_application(app_id, sync=True):
    app = get_application_or_404(app_id)
    for i in store.interviews.all():
        if i["applicationId"] == app_id:
            store.interviews.delete(i["id"])
    store.applications.delete(app_id)
    if sync:
        sync_placed(app["studentId"])


# ---------- interviews ----------
def _check_clash(student_id, date_str, time_str, ignore_id=None):
    apps = {a["id"]: a for a in store.applications.all()}
    for i in store.interviews.all():
        if i["id"] == ignore_id:
            continue
        other = apps.get(i["applicationId"])
        if other and other["studentId"] == student_id and i["date"] == date_str and i["time"] == time_str:
            raise ConflictError("This student already has an interview at this date and time")


def create_interview(clean):
    app = get_application_or_404(clean["applicationId"])
    if app["status"] != "Shortlisted":
        raise ApiError("Only shortlisted applications can be scheduled for an interview "
                       f"(current status: {app['status']})", 422)
    if any(i["applicationId"] == app["id"] for i in store.interviews.all()):
        raise ConflictError("This application already has an interview")
    _check_clash(app["studentId"], clean["date"], clean["time"])
    iv = store.interviews.insert(clean)
    store.applications.update(app["id"], {"status": "Interview Scheduled"})
    return iv


def update_interview(iv_id, clean):
    iv = get_interview_or_404(iv_id)
    app = get_application_or_404(iv["applicationId"])
    _check_clash(app["studentId"], clean["date"], clean["time"], ignore_id=iv_id)
    return store.interviews.update(iv_id, clean)


def delete_interview(iv_id):
    iv = get_interview_or_404(iv_id)
    store.interviews.delete(iv_id)
    app = store.applications.get(iv["applicationId"])
    if app and app["status"] == "Interview Scheduled":
        store.applications.update(app["id"], {"status": "Shortlisted"})


# ---------- dashboard ----------
def dashboard_summary():
    studs, jobs, apps = store.students.all(), store.jobs.all(), store.applications.all()
    placed = sum(1 for s in studs if s["placed"])
    counts = {}
    for a in apps:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    today = date.today().isoformat()
    return {
        "totalStudents": len(studs),
        "placedStudents": placed,
        "placementRate": round(placed / len(studs) * 100) if studs else 0,
        "totalJobs": len(jobs),
        "openJobs": sum(1 for j in jobs if j["status"] == "Open"),
        "totalApplications": len(apps),
        "statusCounts": counts,
        "upcomingInterviews": sum(1 for i in store.interviews.all() if i["date"] >= today),
        # Legacy snake_case aliases
        "total_students": len(studs),
        "available_jobs": sum(1 for j in jobs if j["status"] == "Open"),
        "total_applications": len(apps),
        "selected_students": placed,
    }


def dashboard_analytics():
    studs, jobs, apps = store.students.all(), store.jobs.all(), store.applications.all()
    dept_stats = {}
    for s in studs:
        d = s["department"]
        if d not in dept_stats:
            dept_stats[d] = {"total": 0, "placed": 0, "avgCgpa": 0.0}
        dept_stats[d]["total"] += 1
        if s["placed"]:
            dept_stats[d]["placed"] += 1
        dept_stats[d]["avgCgpa"] += s["cgpa"]
    for d, st in dept_stats.items():
        st["avgCgpa"] = round(st["avgCgpa"] / st["total"], 2) if st["total"] else 0.0
        st["placementRate"] = round((st["placed"] / st["total"]) * 100) if st["total"] else 0

    packages = [j["package"] for j in jobs if j.get("package")]
    salary_stats = {
        "highest": max(packages) if packages else 0.0,
        "average": round(sum(packages) / len(packages), 2) if packages else 0.0,
        "lowest": min(packages) if packages else 0.0,
    }

    status_funnel = {}
    for a in apps:
        st = a["status"]
        status_funnel[st] = status_funnel.get(st, 0) + 1

    summary = dashboard_summary()
    return {
        **summary,
        "departmentStats": dept_stats,
        "salaryStats": salary_stats,
        "statusFunnel": status_funnel,
    }
