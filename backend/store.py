"""SQL-backed data store with automatic table migrations and compatibility layer."""
import copy
import json
import threading
from datetime import date, timedelta

import database

_lock = threading.RLock()


def _d(offset_days):
    return (date.today() + timedelta(days=offset_days)).isoformat()


def _format_student(r):
    if not r:
        return None
    d = dict(r)
    return {
        "id": int(d["id"]),
        "name": str(d.get("name") or ""),
        "rollNo": str(d.get("rollNo") or f"21ST{d['id']:03d}"),
        "email": str(d.get("email") or ""),
        "department": str(d.get("department") or ""),
        "cgpa": float(d.get("cgpa") or 0.0),
        "backlogs": int(d.get("backlogs") or 0),
        "year": int(d.get("year") or 4),
        "skills": str(d.get("skills") or ""),
        "placed": bool(d.get("placed")),
    }


def _format_job(r):
    if not r:
        return None
    d = dict(r)
    role = str(d.get("role") or d.get("job_role") or "")
    min_cgpa = float(d.get("minCgpa") if d.get("minCgpa") is not None else d.get("minimum_cgpa") or 0.0)
    raw_deps = d.get("departments")
    if isinstance(raw_deps, list):
        deps = raw_deps
    elif isinstance(raw_deps, str):
        try:
            deps = json.loads(raw_deps)
        except Exception:
            deps = [x.strip() for x in raw_deps.split(",") if x.strip()]
    else:
        deps = ["AI & DS", "CSE", "IT", "ECE"]

    return {
        "id": int(d["id"]),
        "company": str(d.get("company") or ""),
        "role": role,
        "job_role": role,
        "package": float(d.get("package") or 0.0),
        "location": str(d.get("location") or "Chennai"),
        "minCgpa": min_cgpa,
        "minimum_cgpa": min_cgpa,
        "maxBacklogs": int(d.get("maxBacklogs") or 0),
        "departments": deps,
        "deadline": str(d.get("deadline") or _d(30)),
        "status": str(d.get("status") or "Open"),
    }


def _format_application(r):
    if not r:
        return None
    d = dict(r)
    sid = int(d.get("studentId") if d.get("studentId") is not None else d.get("student_id") or 0)
    jid = int(d.get("jobId") if d.get("jobId") is not None else d.get("job_id") or 0)
    status = str(d.get("status") or "Applied")
    if status == "Interview":
        status = "Interview Scheduled"
    return {
        "id": int(d["id"]),
        "studentId": sid,
        "student_id": sid,
        "jobId": jid,
        "job_id": jid,
        "appliedOn": str(d.get("appliedOn") or _d(-1)),
        "status": status,
    }


def _format_interview(r):
    if not r:
        return None
    d = dict(r)
    aid = int(d.get("applicationId") if d.get("applicationId") is not None else d.get("application_id") or 0)
    return {
        "id": int(d["id"]),
        "applicationId": aid,
        "application_id": aid,
        "date": str(d.get("date") or _d(5)),
        "time": str(d.get("time") or "10:00"),
        "mode": str(d.get("mode") or "Online"),
        "venue": str(d.get("venue") or "Google Meet"),
    }


class SqlTable:
    def __init__(self, table_name, formatter):
        self.table_name = table_name
        self.formatter = formatter

    def all(self):
        with _lock:
            conn = database.get_db()
            c = conn.cursor()
            rows = c.execute(f"SELECT * FROM {self.table_name} ORDER BY id ASC").fetchall()
            return [self.formatter(r) for r in rows]

    def get(self, row_id):
        with _lock:
            conn = database.get_db()
            c = conn.cursor()
            row = c.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (row_id,)).fetchone()
            return self.formatter(row)

    def insert(self, row):
        with _lock:
            conn = database.get_db()
            c = conn.cursor()
            row = copy.deepcopy(row)

            if self.table_name == "students":
                cols = ["name", "rollNo", "email", "department", "cgpa", "backlogs", "year", "skills", "placed"]
                vals = [
                    row.get("name"),
                    row.get("rollNo"),
                    row.get("email"),
                    row.get("department"),
                    float(row.get("cgpa", 0.0)),
                    int(row.get("backlogs", 0)),
                    int(row.get("year", 4)),
                    row.get("skills", ""),
                    1 if row.get("placed") else 0,
                ]
            elif self.table_name == "jobs":
                cols = [
                    "company", "role", "job_role", "package", "location",
                    "minCgpa", "minimum_cgpa", "maxBacklogs", "departments", "deadline", "status"
                ]
                role = row.get("role") or row.get("job_role", "")
                min_cgpa = float(row.get("minCgpa") if row.get("minCgpa") is not None else row.get("minimum_cgpa", 0.0))
                deps = row.get("departments", [])
                deps_json = json.dumps(deps) if isinstance(deps, list) else str(deps)
                vals = [
                    row.get("company"), role, role, float(row.get("package", 0.0)),
                    row.get("location", "Chennai"), min_cgpa, min_cgpa,
                    int(row.get("maxBacklogs", 0)), deps_json,
                    row.get("deadline", _d(30)), row.get("status", "Open"),
                ]
            elif self.table_name == "applications":
                cols = ["studentId", "student_id", "jobId", "job_id", "appliedOn", "status"]
                sid = row.get("studentId") or row.get("student_id")
                jid = row.get("jobId") or row.get("job_id")
                vals = [sid, sid, jid, jid, row.get("appliedOn", _d(0)), row.get("status", "Applied")]
            elif self.table_name == "interviews":
                cols = ["applicationId", "date", "time", "mode", "venue"]
                aid = row.get("applicationId") or row.get("application_id")
                vals = [aid, row.get("date"), row.get("time"), row.get("mode", "Online"), row.get("venue", "")]
            else:
                cols = list(row.keys())
                vals = list(row.values())

            if row.get("id"):
                cols.insert(0, "id")
                vals.insert(0, row["id"])

            placeholders = ", ".join(["?"] * len(vals))
            col_names = ", ".join(cols)
            sql = f"INSERT INTO {self.table_name} ({col_names}) VALUES ({placeholders})"
            c.execute(sql, vals)
            new_id = row.get("id") or c.lastrowid
            conn.commit()
            return self.get(new_id)

    def update(self, row_id, changes):
        with _lock:
            existing = self.get(row_id)
            if not existing:
                return None
            conn = database.get_db()
            c = conn.cursor()

            set_clauses = []
            vals = []
            for k, v in changes.items():
                if k == "id":
                    continue
                if k == "placed":
                    v = 1 if v else 0
                elif k == "departments" and isinstance(v, list):
                    v = json.dumps(v)
                elif k == "role":
                    set_clauses.append("job_role = ?")
                    vals.append(v)
                elif k == "minCgpa":
                    set_clauses.append("minimum_cgpa = ?")
                    vals.append(v)
                elif k == "studentId":
                    set_clauses.append("student_id = ?")
                    vals.append(v)
                elif k == "jobId":
                    set_clauses.append("job_id = ?")
                    vals.append(v)

                set_clauses.append(f"{k} = ?")
                vals.append(v)

            if set_clauses:
                vals.append(row_id)
                sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE id = ?"
                c.execute(sql, vals)
                conn.commit()
            return self.get(row_id)

    def delete(self, row_id):
        with _lock:
            existing = self.get(row_id)
            if not existing:
                return False
            conn = database.get_db()
            c = conn.cursor()
            c.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (row_id,))
            conn.commit()
            return True

    def clear(self):
        with _lock:
            conn = database.get_db()
            c = conn.cursor()
            c.execute(f"DELETE FROM {self.table_name}")
            conn.commit()


students = SqlTable("students", _format_student)
jobs = SqlTable("jobs", _format_job)
applications = SqlTable("applications", _format_application)
interviews = SqlTable("interviews", _format_interview)


def seed():
    """Seed data used for demo / tests. Dates are relative to today."""
    with _lock:
        for t in (interviews, applications, jobs, students):
            t.clear()

        for s in [
            (1, "Aarav Sharma", "21AD001", "aarav@college.edu", "AI & DS", 8.9, 0, "Python, ML, SQL", True),
            (2, "Priya Nair", "21AD014", "priya@college.edu", "AI & DS", 9.2, 0, "Java, Spring, AWS", False),
            (3, "Rohan Mehta", "21CS022", "rohan@college.edu", "CSE", 7.4, 1, "React, Node.js", False),
            (4, "Sneha Iyer", "21IT007", "sneha@college.edu", "IT", 8.1, 0, "Python, Django", True),
            (5, "Karthik Raj", "21AD031", "karthik@college.edu", "AI & DS", 6.8, 2, "C++, DSA", False),
            (6, "Divya Lakshmi", "21EC018", "divya@college.edu", "ECE", 8.5, 0, "Embedded C, IoT", False),
        ]:
            students.insert({
                "id": s[0], "name": s[1], "rollNo": s[2], "email": s[3], "department": s[4],
                "cgpa": s[5], "backlogs": s[6], "year": 4, "skills": s[7], "placed": s[8]
            })

        for j in [
            (1, "TCS", "Software Engineer", 7.0, "Chennai", 6.5, 1, ["CSE", "IT", "AI & DS", "ECE"], _d(18), "Open"),
            (2, "Zoho", "Member Technical Staff", 9.5, "Chennai", 8.0, 0, ["CSE", "IT", "AI & DS"], _d(13), "Open"),
            (3, "Infosys", "Systems Engineer", 6.5, "Bengaluru", 6.0, 2, ["CSE", "IT", "AI & DS", "ECE"], _d(-8), "Closed"),
            (4, "Amazon", "SDE - I", 28.0, "Hyderabad", 8.5, 0, ["CSE", "IT", "AI & DS"], _d(33), "Open"),
        ]:
            jobs.insert({
                "id": j[0], "company": j[1], "role": j[2], "package": j[3], "location": j[4],
                "minCgpa": j[5], "maxBacklogs": j[6], "departments": j[7], "deadline": j[8], "status": j[9]
            })

        for a in [
            (1, 1, 1, _d(-13), "Selected"),
            (2, 2, 2, _d(-5), "Interview Scheduled"),
            (3, 2, 4, _d(-3), "Shortlisted"),
            (4, 3, 1, _d(-11), "Applied"),
            (5, 4, 3, _d(-23), "Selected"),
            (6, 5, 3, _d(-22), "Rejected"),
            (7, 6, 1, _d(-4), "Interview Scheduled"),
        ]:
            applications.insert({
                "id": a[0], "studentId": a[1], "jobId": a[2], "appliedOn": a[3], "status": a[4]
            })

        interviews.insert({
            "id": 1, "applicationId": 2, "date": _d(4), "time": "10:00", "mode": "Online", "venue": "Google Meet"
        })
        interviews.insert({
            "id": 2, "applicationId": 7, "date": _d(6), "time": "14:30", "mode": "Offline", "venue": "Seminar Hall A"
        })


# Initialize database schema and migrate without erasing existing data
database.init_db()

# If the database is completely empty (brand new setup), seed it
if not students.all():
    seed()
