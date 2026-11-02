from flask import Blueprint, jsonify, request

import services
import store
from routes import json_body
from validators import validate_student

bp = Blueprint("students", __name__, url_prefix="/api/students")


@bp.get("")
def list_students():
    q = request.args.get("q", "").strip().lower()
    dept = request.args.get("department", "").strip()
    rows = [s for s in store.students.all()
            if (not dept or s["department"] == dept)
            and (not q or q in f"{s['name']} {s['rollNo']} {s['email']}".lower())]
    return jsonify(rows)


@bp.post("")
def create_student():
    student = services.create_student(validate_student(json_body()))
    return jsonify(student), 201


@bp.get("/<int:student_id>")
def get_student(student_id):
    return jsonify(services.get_student_or_404(student_id))


@bp.put("/<int:student_id>")
def update_student(student_id):
    return jsonify(services.update_student(student_id, validate_student(json_body())))


@bp.delete("/<int:student_id>")
def delete_student(student_id):
    services.delete_student(student_id)
    return jsonify({"message": "Student deleted"})


@bp.post("/login")
def student_login():
    data = json_body()
    identifier = (data.get("identifier") or data.get("email") or data.get("rollNo") or "").strip().lower()
    if not identifier:
        return jsonify({"error": "Email or Roll Number is required", "status": 400}), 400
    for s in store.students.all():
        if s["email"].lower() == identifier or s["rollNo"].lower() == identifier:
            return jsonify({
                "token": f"student-{s['id']}-token",
                "role": "student",
                "user": s,
            })
    return jsonify({"error": "Student not found", "status": 401}), 401
