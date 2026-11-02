"""Custom errors and one place that turns every error into clean JSON."""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    status = 400

    def __init__(self, message, status=None, details=None):
        super().__init__(message)
        self.message = message
        if status:
            self.status = status
        self.details = details


class ValidationError(ApiError):
    def __init__(self, details, message="Validation failed"):
        super().__init__(message, 422, details)


class NotFoundError(ApiError):
    def __init__(self, what="Resource"):
        super().__init__(f"{what} not found", 404)


class ConflictError(ApiError):
    def __init__(self, message, details=None):
        super().__init__(message, 409, details)


def _json_error(message, status, details=None):
    body = {"error": message, "status": status}
    if details:
        body["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        return _json_error(e.message, e.status, e.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(e):
        return _json_error(e.description or e.name, e.code)

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        app.logger.exception("Unhandled error")
        return _json_error("Internal server error", 500)
