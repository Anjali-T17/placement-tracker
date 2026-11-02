from flask import Blueprint, jsonify, request

import services
import store
from routes import json_body
from validators import JOB_STATUSES, validate_job

bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@bp.get("")
def list_jobs():
    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "").strip()
    if status and status not in JOB_STATUSES:
        return jsonify({"error": f"status must be one of: {', '.join(JOB_STATUSES)}", "status": 400}), 400
    rows = [j for j in store.jobs.all()
            if (not status or j["status"] == status)
            and (not q or q in f"{j['company']} {j['role']}".lower())]
    return jsonify(rows)


@bp.post("")
def create_job():
    return jsonify(store.jobs.insert(validate_job(json_body()))), 201


@bp.get("/<int:job_id>")
def get_job(job_id):
    return jsonify(services.get_job_or_404(job_id))


@bp.put("/<int:job_id>")
def update_job(job_id):
    services.get_job_or_404(job_id)
    return jsonify(store.jobs.update(job_id, validate_job(json_body())))


@bp.delete("/<int:job_id>")
def delete_job(job_id):
    services.delete_job(job_id)
    return jsonify({"message": "Job deleted"})
