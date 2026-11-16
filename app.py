import os
import secrets
import sqlite3
from contextlib import closing
from urllib.parse import urlsplit

from flask import Flask, abort, current_app, g, jsonify, redirect, render_template, request
from werkzeug.exceptions import HTTPException


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "DATABASE_PATH", os.path.join(app.instance_path, "urls.sqlite3")
        ),
        PUBLIC_BASE_URL=os.environ.get("PUBLIC_BASE_URL", "").rstrip("/"),
        TRUSTED_HOSTS=[
            host.strip()
            for host in os.environ.get(
                "TRUSTED_HOSTS", "localhost,127.0.0.1,::1"
            ).split(",")
            if host.strip()
        ],
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    with closing(sqlite3.connect(app.config["DATABASE"])) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    @app.teardown_appcontext
    def close_db(_error: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify(error=error.description), error.code

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.post("/api/shorten")
    def shorten_url():
        if not request.is_json:
            return jsonify(error="Send the request as application/json."), 415

        payload = request.get_json()
        if not isinstance(payload, dict):
            return jsonify(error="The JSON body must be an object."), 400

        original_url = payload.get("url")
        if not isinstance(original_url, str) or not original_url:
            return jsonify(error="A non-empty 'url' string is required."), 400
        if len(original_url) > 2048 or any(char.isspace() for char in original_url):
            return jsonify(error="The URL must be at most 2048 characters with no spaces."), 400

        try:
            parsed_url = urlsplit(original_url)
            host = parsed_url.hostname
            parsed_url.port
        except ValueError:
            return jsonify(error="Enter a valid HTTP or HTTPS URL."), 400

        if (
            parsed_url.scheme.lower() not in {"http", "https"}
            or not parsed_url.netloc
            or not host
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            return jsonify(error="Enter a valid HTTP or HTTPS URL."), 400

        db = get_db()
        for _attempt in range(5):
            code = secrets.token_urlsafe(6)
            try:
                db.execute(
                    "INSERT INTO links (code, original_url) VALUES (?, ?)",
                    (code, original_url),
                )
                db.commit()
                base_url = (
                    current_app.config["PUBLIC_BASE_URL"]
                    or request.url_root.rstrip("/")
                )
                return (
                    jsonify(
                        code=code,
                        original_url=original_url,
                        short_url=f"{base_url}/s/{code}",
                    ),
                    201,
                )
            except sqlite3.IntegrityError:
                db.rollback()

        current_app.logger.error("Could not allocate a unique short URL after 5 attempts.")
        return jsonify(error="Unable to create a short URL right now."), 503

    @app.get("/s/<string:code>")
    def follow_short_url(code: str):
        link = get_db().execute(
            "SELECT original_url FROM links WHERE code = ?", (code,)
        ).fetchone()
        if link is None:
            abort(404, description="Short URL not found.")
        return redirect(link["original_url"], code=302)

    @app.get("/api/links/<string:code>")
    def get_link(code: str):
        link = get_db().execute(
            "SELECT code, original_url, created_at FROM links WHERE code = ?",
            (code,),
        ).fetchone()
        if link is None:
            abort(404, description="Short URL not found.")
        return jsonify(dict(link))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
