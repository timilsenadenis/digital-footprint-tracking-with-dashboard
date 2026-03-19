"""
Digital Footprint Tracker — Flask REST API
Endpoints for browser extension to POST data + dashboard to GET analytics
"""

from flask import Flask, request, jsonify, g, render_template
from functools import wraps
import psycopg2
import psycopg2.extras
import os
import jwt
import datetime
import hashlib

app = Flask(__name__, template_folder="../dashboard/templates",
            static_folder="../dashboard/static")

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://footprint:footprint@localhost:5432/footprint_db")

# ─────────────────────────────────────────
#  DB connection
# ─────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

# ─────────────────────────────────────────
#  Auth decorator (JWT + RLS)
# ─────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            g.user_id = payload["user_id"]
            # Set PostgreSQL session variable for RLS
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SET app.current_user_id = %s", (g.user_id,))
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([username, email, password]):
        return jsonify({"error": "username, email and password are required"}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s,%s,%s) RETURNING id, api_key",
                (username, email, pw_hash)
            )
            row = cur.fetchone()
            db.commit()
        return jsonify({"user_id": str(row["id"]), "api_key": str(row["api_key"])}), 201
    except psycopg2.errors.UniqueViolation:
        db.rollback()
        return jsonify({"error": "Username or email already exists"}), 409

@app.route("/api/login", methods=["POST"])
def login():
    data    = request.json or {}
    email   = data.get("email", "").strip().lower()
    password = data.get("password", "")
    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email=%s AND password_hash=%s", (email, pw_hash))
        user = cur.fetchone()

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode({
        "user_id": str(user["id"]),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"token": token})

# ─────────────────────────────────────────
#  TRACKING ROUTES (called by extension)
# ─────────────────────────────────────────
@app.route("/api/track/visit", methods=["POST"])
@require_auth
def track_visit():
    data = request.json or {}
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO visits (user_id, url, page_title, visit_start, visit_end,
                                device_type, browser, is_incognito, raw_payload)
            VALUES (%s, %s, %s,
                    to_timestamp(%s), to_timestamp(%s),
                    %s, %s, %s, %s)
            RETURNING id
        """, (
            g.user_id,
            data.get("url"),
            data.get("title"),
            data.get("start_ts"),
            data.get("end_ts"),
            data.get("device", "desktop"),
            data.get("browser", "chrome"),
            data.get("incognito", False),
            psycopg2.extras.Json(data)
        ))
        row = cur.fetchone()
        db.commit()
    return jsonify({"id": row["id"]}), 201

@app.route("/api/track/search", methods=["POST"])
@require_auth
def track_search():
    data = request.json or {}
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO searches (user_id, query, engine, results_clicked, searched_at, raw_payload)
            VALUES (%s, %s, %s, %s, to_timestamp(%s), %s)
            RETURNING id
        """, (
            g.user_id,
            data.get("query"),
            data.get("engine", "google"),
            data.get("results_clicked", 0),
            data.get("timestamp"),
            psycopg2.extras.Json(data)
        ))
        row = cur.fetchone()
        db.commit()
    return jsonify({"id": row["id"]}), 201

@app.route("/api/track/social", methods=["POST"])
@require_auth
def track_social():
    data = request.json or {}
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO social_events (user_id, platform, action, content_type,
                                       time_spent_sec, event_at, raw_payload)
            VALUES (%s, %s, %s, %s, %s, to_timestamp(%s), %s)
            RETURNING id
        """, (
            g.user_id,
            data.get("platform"),
            data.get("action"),
            data.get("content_type"),
            data.get("time_spent_sec", 0),
            data.get("timestamp"),
            psycopg2.extras.Json(data)
        ))
        row = cur.fetchone()
        db.commit()
    return jsonify({"id": row["id"]}), 201

@app.route("/api/track/app", methods=["POST"])
@require_auth
def track_app():
    data = request.json or {}
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            INSERT INTO app_usage (user_id, app_name, session_start, session_end, raw_payload)
            VALUES (%s, %s, to_timestamp(%s), to_timestamp(%s), %s)
            RETURNING id
        """, (
            g.user_id,
            data.get("app_name"),
            data.get("start_ts"),
            data.get("end_ts"),
            psycopg2.extras.Json(data)
        ))
        row = cur.fetchone()
        db.commit()
    return jsonify({"id": row["id"]}), 201

# ─────────────────────────────────────────
#  ANALYTICS ROUTES (called by dashboard)
# ─────────────────────────────────────────
@app.route("/api/analytics/summary", methods=["GET"])
@require_auth
def analytics_summary():
    """Return daily summary for the last N days."""
    days = int(request.args.get("days", 7))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT day, total_visits, unique_domains,
                   total_time_sec, social_visits,
                   entertainment_visits, productivity_visits
            FROM daily_summary
            WHERE user_id = %s AND day >= CURRENT_DATE - %s
            ORDER BY day
        """, (g.user_id, days))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analytics/top-domains", methods=["GET"])
@require_auth
def analytics_top_domains():
    limit = int(request.args.get("limit", 10))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT domain, COUNT(*) AS visits,
                   SUM(duration_sec) AS total_sec,
                   c.name AS category, c.color_hex
            FROM visits v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.user_id = %s AND v.visit_start >= NOW() - INTERVAL '7 days'
            GROUP BY domain, c.name, c.color_hex
            ORDER BY visits DESC
            LIMIT %s
        """, (g.user_id, limit))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analytics/heatmap", methods=["GET"])
@require_auth
def analytics_heatmap():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT day_of_week, hour_of_day, visit_count, total_sec
            FROM hourly_activity_heatmap
            WHERE user_id = %s
        """, (g.user_id,))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analytics/categories", methods=["GET"])
@require_auth
def analytics_categories():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT c.name, c.color_hex,
                   COUNT(*) AS visits,
                   SUM(v.duration_sec) AS total_sec
            FROM visits v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.user_id = %s AND v.visit_start >= NOW() - INTERVAL '30 days'
            GROUP BY c.name, c.color_hex
            ORDER BY visits DESC
        """, (g.user_id,))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analytics/searches", methods=["GET"])
@require_auth
def analytics_searches():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT keyword, frequency, last_searched
            FROM search_keyword_frequency
            WHERE user_id = %s
            LIMIT 50
        """, (g.user_id,))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analytics/social", methods=["GET"])
@require_auth
def analytics_social():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT platform,
                   COUNT(*) AS events,
                   SUM(time_spent_sec) AS total_sec,
                   COUNT(*) FILTER (WHERE action='post')    AS posts,
                   COUNT(*) FILTER (WHERE action='like')    AS likes,
                   COUNT(*) FILTER (WHERE action='scroll')  AS scrolls
            FROM social_events
            WHERE user_id = %s AND event_at >= NOW() - INTERVAL '7 days'
            GROUP BY platform
            ORDER BY total_sec DESC
        """, (g.user_id,))
        rows = cur.fetchall()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────
#  DASHBOARD ROUTE
# ─────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)