from flask import Blueprint, jsonify

import services
import store
from routes import json_body
from validators import validate_interview

bp = Blueprint("interviews", __name__, url_prefix="/api/interviews")


@bp.get("")
def list_interviews():
    rows = sorted(store.interviews.all(), key=lambda i: (i["date"], i["time"]))
    return jsonify(rows)


@bp.post("")
def create_interview():
    clean = validate_interview(json_body(), creating=True)
    return jsonify(services.create_interview(clean)), 201


@bp.get("/<int:iv_id>")
def get_interview(iv_id):
    return jsonify(services.get_interview_or_404(iv_id))


@bp.put("/<int:iv_id>")
def update_interview(iv_id):
    clean = validate_interview(json_body(), creating=False)
    return jsonify(services.update_interview(iv_id, clean))


@bp.delete("/<int:iv_id>")
def delete_interview(iv_id):
    services.delete_interview(iv_id)
    return jsonify({"message": "Interview cancelled"})
