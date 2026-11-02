from flask import Blueprint, jsonify, request

import services
import store
from errors import ApiError

bp = Blueprint("eligibility", __name__, url_prefix="/api/eligibility")


def _required_int(name):
    raw = request.args.get(name)
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise ApiError(f"Query parameter '{name}' is required and must be a whole number", 400)


@bp.get("/check")
def check_one():
    student = services.get_student_or_404(_required_int("studentId"))
    job = services.get_job_or_404(_required_int("jobId"))
    result = services.check_eligibility(student, job)
    return jsonify({
        "student": {"id": student["id"], "name": student["name"]},
        "job": {"id": job["id"], "company": job["company"], "role": job["role"]},
        **result,
    })


@bp.get("/job/<int:job_id>")
def students_for_job(job_id):
    job = services.get_job_or_404(job_id)
    rows = []
    for s in store.students.all():
        r = services.check_eligibility(s, job)
        rows.append({"studentId": s["id"], "name": s["name"], "rollNo": s["rollNo"],
                     "department": s["department"], "cgpa": s["cgpa"], "backlogs": s["backlogs"], **r})
    return jsonify(rows)


@bp.get("/student/<int:student_id>")
def jobs_for_student(student_id):
    student = services.get_student_or_404(student_id)
    rows = []
    for j in store.jobs.all():
        r = services.check_eligibility(student, j)
        rows.append({"jobId": j["id"], "company": j["company"], "role": j["role"], **r})
    return jsonify(rows)
