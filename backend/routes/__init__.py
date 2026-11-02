from flask import request

from errors import ApiError


def json_body():
    """Return the JSON body as a dict, or raise a clean 400 error."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return data


def register_blueprints(app):
    from routes.applications import bp as applications_bp
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.eligibility import bp as eligibility_bp
    from routes.interviews import bp as interviews_bp
    from routes.jobs import bp as jobs_bp
    from routes.students import bp as students_bp

    for bp in (students_bp, jobs_bp, applications_bp, interviews_bp, eligibility_bp, dashboard_bp, auth_bp):
        app.register_blueprint(bp)
