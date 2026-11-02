"""Flask entry point for the College Placement Application Tracker API."""
from flask import Flask, jsonify, request

from config import Config
from errors import register_error_handlers
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config["CORS_ORIGINS"] = Config.CORS_ORIGINS
    app.json.sort_keys = False

    register_error_handlers(app)
    register_blueprints(app)

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            resp = app.make_default_options_response()
            return add_cors_headers(resp)

    @app.after_request
    def add_cors_headers(resp):
        """Allow only the configured frontend origins to call the API."""
        origin = request.headers.get("Origin")
        if origin and (origin in app.config["CORS_ORIGINS"] or "*" in app.config["CORS_ORIGINS"]):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Accept"
        return resp

    @app.get("/")
    def index():
        return jsonify({"name": "College Placement Application Tracker API", "docs": "/api/health"})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
