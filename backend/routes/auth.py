from flask import Blueprint, jsonify, request

import services
import store
from errors import ApiError
from routes import json_body
from validators import validate_student

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    """Register a new student account."""
    clean = validate_student(json_body())
    student = services.create_student(clean)
    token = f"student-{student['id']}-token"
    return jsonify({
        "message": "Student registration successful",
        "token": token,
        "user": student,
        "role": "student",
    }), 201


@bp.post("/login")
def login():
    """Login with email, roll number, or admin credentials."""
    data = json_body()
    identifier = (data.get("identifier") or data.get("email") or data.get("rollNo") or "").strip().lower()

    if not identifier:
        raise ApiError("Email or Roll Number is required", 400)

    # Admin check
    if identifier in ("admin", "admin@college.edu"):
        return jsonify({
            "token": "admin-token",
            "role": "admin",
            "user": {
                "id": 0,
                "name": "Placement Coordinator",
                "email": "admin@college.edu",
                "role": "admin",
            },
        })

    # Search students
    for s in store.students.all():
        if s["email"].lower() == identifier or s["rollNo"].lower() == identifier:
            return jsonify({
                "token": f"student-{s['id']}-token",
                "role": "student",
                "user": s,
            })

    raise ApiError("Invalid credentials: No student found with this email or roll number", 401)


@bp.get("/me")
def me():
    """Get currently authenticated user info based on Authorization header or param."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header else request.args.get("token", "")

    if token == "admin-token":
        return jsonify({
            "role": "admin",
            "user": {
                "id": 0,
                "name": "Placement Coordinator",
                "email": "admin@college.edu",
                "role": "admin",
            },
        })

    if token.startswith("student-"):
        try:
            sid = int(token.split("-")[1])
            student = services.get_student_or_404(sid)
            return jsonify({"role": "student", "user": student})
        except Exception:
            pass

    # Default to coordinator profile
    return jsonify({
        "role": "admin",
        "user": {
            "id": 0,
            "name": "Placement Coordinator",
            "email": "admin@college.edu",
            "role": "admin",
        },
    })
