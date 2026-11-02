from flask import Blueprint, jsonify, request

import services
import store
from errors import ApiError
from routes import json_body
from validators import APPLICATION_STATUSES, validate_application, validate_status_change

bp = Blueprint("applications", __name__, url_prefix="/api/applications")


def _int_arg(name):
    raw = request.args.get(name)
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except ValueError:
        raise ApiError(f"{name} must be a whole number", 400)


@bp.get("")
def list_applications():
    student_id, job_id = _int_arg("studentId"), _int_arg("jobId")
    status = request.args.get("status", "").strip()
    if status and status not in APPLICATION_STATUSES:
        raise ApiError(f"status must be one of: {', '.join(APPLICATION_STATUSES)}", 400)
    rows = [a for a in store.applications.all()
            if (student_id is None or a["studentId"] == student_id)
            and (job_id is None or a["jobId"] == job_id)
            and (not status or a["status"] == status)]
    return jsonify(rows)


@bp.post("")
def create_application():
    clean = validate_application(json_body())
    return jsonify(services.create_application(clean["studentId"], clean["jobId"])), 201


@bp.get("/<int:app_id>")
def get_application(app_id):
    return jsonify(services.get_application_or_404(app_id))


@bp.patch("/<int:app_id>/status")
def change_status(app_id):
    clean = validate_status_change(json_body())
    return jsonify(services.change_application_status(app_id, clean["status"]))


@bp.delete("/<int:app_id>")
def delete_application(app_id):
    services.delete_application(app_id)
    return jsonify({"message": "Application withdrawn"})
