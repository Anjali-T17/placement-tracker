from flask import Blueprint, jsonify

import services

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("")
@bp.get("/summary")
def summary():
    return jsonify(services.dashboard_summary())


@bp.get("/analytics")
def analytics():
    return jsonify(services.dashboard_analytics())
