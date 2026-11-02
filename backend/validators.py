"""Input validation. Every function returns CLEAN data or raises ValidationError."""
import re
from datetime import date, datetime

from errors import ValidationError

DEPARTMENTS = ["AI & DS", "CSE", "IT", "ECE"]
APPLICATION_STATUSES = ["Applied", "Shortlisted", "Interview Scheduled", "Selected", "Rejected"]
JOB_STATUSES = ["Open", "Closed"]
INTERVIEW_MODES = ["Online", "Offline"]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ROLL_RE = re.compile(r"^[A-Z0-9]{4,15}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


# ---------- small helpers ----------
def _text(data, key, errors, label, *, max_len=100, min_len=1, required=True, default=""):
    v = data.get(key)
    if v is None or (isinstance(v, str) and v.strip() == ""):
        if required:
            errors[key] = f"{label} is required"
        return default
    if not isinstance(v, str):
        errors[key] = f"{label} must be text"
        return default
    v = v.strip()
    if len(v) < min_len:
        errors[key] = f"{label} must be at least {min_len} characters"
        return default
    if len(v) > max_len:
        errors[key] = f"{label} must be at most {max_len} characters"
        return default
    return v


def _number(data, key, errors, label, *, min_v, max_v, integer=False, required=True, default=None):
    v = data.get(key)
    if v is None or v == "":
        if required:
            errors[key] = f"{label} is required"
        return default
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        errors[key] = f"{label} must be a number"
        return default
    if integer and isinstance(v, float) and not v.is_integer():
        errors[key] = f"{label} must be a whole number"
        return default
    if not (min_v <= v <= max_v):
        errors[key] = f"{label} must be between {min_v} and {max_v}"
        return default
    return int(v) if integer else float(v)


def _date(data, key, errors, label, *, allow_past=True):
    v = data.get(key)
    if not v:
        errors[key] = f"{label} is required"
        return None
    try:
        d = datetime.strptime(v, "%Y-%m-%d").date() if isinstance(v, str) else None
    except ValueError:
        d = None
    if d is None:
        errors[key] = f"{label} must be a valid date (YYYY-MM-DD)"
        return None
    if not allow_past and d < date.today():
        errors[key] = f"{label} cannot be in the past"
        return None
    return d.isoformat()


def _choice(data, key, errors, label, choices, *, default=None):
    v = data.get(key, default)
    if v not in choices:
        errors[key] = f"{label} must be one of: {', '.join(choices)}"
        return default
    return v


def _finish(errors, clean):
    if errors:
        raise ValidationError(errors)
    return clean


# ---------- validators ----------
def validate_student(data):
    e = {}
    dept = data.get("department")
    if dept in ("AI&DS", "AI& DS", "AI &DS"):
        data = dict(data, department="AI & DS")
    clean = {
        "name": _text(data, "name", e, "Name", min_len=2),
        "rollNo": _text(data, "rollNo", e, "Roll number", max_len=15).upper(),
        "email": _text(data, "email", e, "Email", max_len=120).lower(),
        "department": _choice(data, "department", e, "Department", DEPARTMENTS),
        "cgpa": _number(data, "cgpa", e, "CGPA", min_v=0, max_v=10),
        "backlogs": _number(data, "backlogs", e, "Backlogs", min_v=0, max_v=50, integer=True),
        "year": _number(data, "year", e, "Year", min_v=1, max_v=4, integer=True, required=False, default=4),
        "skills": _text(data, "skills", e, "Skills", max_len=200, required=False),
    }
    if "rollNo" not in e and not ROLL_RE.match(clean["rollNo"]):
        e["rollNo"] = "Roll number must be 4-15 letters/digits (example: 21AD001)"
    if "email" not in e and not EMAIL_RE.match(clean["email"]):
        e["email"] = "Enter a valid email address"
    placed = data.get("placed", False)
    if not isinstance(placed, bool):
        e["placed"] = "Placed must be true or false"
    clean["placed"] = placed if isinstance(placed, bool) else False
    if clean["cgpa"] is not None:
        clean["cgpa"] = round(clean["cgpa"], 2)
    return _finish(e, clean)


def validate_job(data):
    e = {}
    if "role" not in data and "job_role" in data:
        data = dict(data, role=data["job_role"])
    if "minCgpa" not in data and "minimum_cgpa" in data:
        data = dict(data, minCgpa=data["minimum_cgpa"])

    clean = {
        "company": _text(data, "company", e, "Company"),
        "role": _text(data, "role", e, "Role"),
        "package": _number(data, "package", e, "Package (LPA)", min_v=0.1, max_v=1000),
        "location": _text(data, "location", e, "Location"),
        "minCgpa": _number(data, "minCgpa", e, "Minimum CGPA", min_v=0, max_v=10),
        "maxBacklogs": _number(data, "maxBacklogs", e, "Max backlogs", min_v=0, max_v=50, integer=True),
        "deadline": _date(data, "deadline", e, "Deadline"),
        "status": _choice(data, "status", e, "Status", JOB_STATUSES, default="Open"),
    }
    deps = data.get("departments")
    if not isinstance(deps, list) or not deps:
        e["departments"] = "Select at least one department"
        clean["departments"] = []
    elif any(d not in DEPARTMENTS for d in deps):
        e["departments"] = f"Departments must be from: {', '.join(DEPARTMENTS)}"
        clean["departments"] = []
    else:
        clean["departments"] = list(dict.fromkeys(deps))
    return _finish(e, clean)


def validate_application(data):
    e = {}
    sid = data.get("studentId") if data.get("studentId") is not None else data.get("student_id")
    jid = data.get("jobId") if data.get("jobId") is not None else data.get("job_id")
    clean = {
        "studentId": _number({"sid": sid}, "sid", e, "Student", min_v=1, max_v=10**9, integer=True),
        "jobId": _number({"jid": jid}, "jid", e, "Job", min_v=1, max_v=10**9, integer=True),
    }
    return _finish(e, clean)


def validate_status_change(data):
    e = {}
    st = data.get("status")
    if st == "Interview":
        data = dict(data, status="Interview Scheduled")
    clean = {"status": _choice(data, "status", e, "Status", APPLICATION_STATUSES)}
    return _finish(e, clean)


def validate_interview(data, *, creating):
    e = {}
    clean = {
        "date": _date(data, "date", e, "Interview date", allow_past=False),
        "mode": _choice(data, "mode", e, "Mode", INTERVIEW_MODES),
        "venue": _text(data, "venue", e, "Venue / meeting link", max_len=150),
    }
    t = data.get("time")
    if not t:
        e["time"] = "Interview time is required"
    elif not isinstance(t, str) or not TIME_RE.match(t):
        e["time"] = "Time must be in HH:MM format (24 hours)"
    clean["time"] = t if "time" not in e else None
    if creating:
        aid = data.get("applicationId") if data.get("applicationId") is not None else data.get("application_id")
        clean["applicationId"] = _number(
            {"aid": aid}, "aid", e, "Application", min_v=1, max_v=10**9, integer=True)
    return _finish(e, clean)
