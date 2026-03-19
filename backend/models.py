"""
models.py — Database models and query helpers
Provides clean Python interfaces for all DB operations
"""

import psycopg2
import psycopg2.extras


# ─────────────────────────────────────────
#  Base Model
# ─────────────────────────────────────────
class BaseModel:
    def __init__(self, db_conn):
        self.db = db_conn

    def execute(self, query, params=None, fetch="all"):
        with self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch == "one":
                return cur.fetchone()
            return cur.fetchall()

    def commit_execute(self, query, params=None, returning=False):
        with self.db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            result = cur.fetchone() if returning else None
            self.db.commit()
            return result


# ─────────────────────────────────────────
#  User Model
# ─────────────────────────────────────────
class UserModel(BaseModel):

    def create(self, username, email, password_hash):
        return self.commit_execute("""
            INSERT INTO users (username, email, password_hash)
            VALUES (%s, %s, %s)
            RETURNING id, api_key, created_at
        """, (username, email, password_hash), returning=True)

    def find_by_credentials(self, email, password_hash):
        return self.execute("""
            SELECT id, username, email, api_key, created_at, last_active
            FROM users WHERE email = %s AND password_hash = %s
        """, (email, password_hash), fetch="one")

    def find_by_id(self, user_id):
        return self.execute("""
            SELECT id, username, email, created_at, last_active
            FROM users WHERE id = %s
        """, (user_id,), fetch="one")

    def find_by_api_key(self, api_key):
        return self.execute("""
            SELECT id, username FROM users WHERE api_key = %s
        """, (api_key,), fetch="one")

    def update_last_active(self, user_id):
        self.commit_execute("UPDATE users SET last_active = NOW() WHERE id = %s", (user_id,))


# ─────────────────────────────────────────
#  Visit Model
# ─────────────────────────────────────────
class VisitModel(BaseModel):

    def create(self, user_id, url, title, start_ts, end_ts,
               device="desktop", browser="chrome", incognito=False, payload=None):
        """Domain + category auto-set by DB triggers."""
        return self.commit_execute("""
            INSERT INTO visits (user_id, url, page_title, visit_start, visit_end,
                                device_type, browser, is_incognito, raw_payload)
            VALUES (%s, %s, %s, to_timestamp(%s), to_timestamp(%s),
                    %s, %s, %s, %s)
            RETURNING id, domain, category_id
        """, (user_id, url, title, start_ts, end_ts,
              device, browser, incognito,
              psycopg2.extras.Json(payload or {})), returning=True)

    def get_recent(self, user_id, limit=50):
        return self.execute("""
            SELECT v.id, v.url, v.domain, v.page_title,
                   v.visit_start, v.duration_sec,
                   c.name AS category, c.color_hex
            FROM visits v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.user_id = %s
            ORDER BY v.visit_start DESC LIMIT %s
        """, (user_id, limit))

    def get_top_domains(self, user_id, days=7, limit=10):
        return self.execute("""
            SELECT v.domain, COUNT(*) AS visits,
                   SUM(v.duration_sec) AS total_sec,
                   c.name AS category, c.color_hex
            FROM visits v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.user_id = %s
              AND v.visit_start >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY v.domain, c.name, c.color_hex
            ORDER BY visits DESC LIMIT %s
        """, (user_id, str(days), limit))

    def get_daily_summary(self, user_id, days=7):
        """Reads from the materialized view for performance."""
        return self.execute("""
            SELECT day, total_visits, unique_domains, total_time_sec,
                   social_visits, entertainment_visits, productivity_visits
            FROM daily_summary
            WHERE user_id = %s AND day >= CURRENT_DATE - %s
            ORDER BY day
        """, (user_id, days))

    def get_category_breakdown(self, user_id, days=30):
        return self.execute("""
            SELECT c.name, c.color_hex,
                   COUNT(*) AS visits, SUM(v.duration_sec) AS total_sec
            FROM visits v
            LEFT JOIN categories c ON v.category_id = c.id
            WHERE v.user_id = %s
              AND v.visit_start >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY c.name, c.color_hex ORDER BY visits DESC
        """, (user_id, str(days)))

    def get_heatmap(self, user_id):
        """Visit counts by day-of-week x hour-of-day (from view)."""
        return self.execute("""
            SELECT day_of_week, hour_of_day, visit_count, total_sec
            FROM hourly_activity_heatmap WHERE user_id = %s
        """, (user_id,))

    def get_session_gaps(self, user_id, limit=100):
        """Window function: gap between consecutive visits for session detection."""
        return self.execute("""
            SELECT id, domain, visit_start,
                   LAG(visit_start) OVER (
                       PARTITION BY user_id ORDER BY visit_start
                   ) AS prev_visit,
                   EXTRACT(EPOCH FROM (
                       visit_start - LAG(visit_start) OVER (
                           PARTITION BY user_id ORDER BY visit_start
                       )
                   )) / 60 AS gap_minutes
            FROM visits WHERE user_id = %s
            ORDER BY visit_start DESC LIMIT %s
        """, (user_id, limit))


# ─────────────────────────────────────────
#  Search Model
# ─────────────────────────────────────────
class SearchModel(BaseModel):

    def create(self, user_id, query, engine, results_clicked=0, timestamp=None, payload=None):
        return self.commit_execute("""
            INSERT INTO searches (user_id, query, engine, results_clicked,
                                  searched_at, raw_payload)
            VALUES (%s, %s, %s, %s, COALESCE(to_timestamp(%s), NOW()), %s)
            RETURNING id
        """, (user_id, query, engine, results_clicked,
              timestamp, psycopg2.extras.Json(payload or {})), returning=True)

    def get_recent(self, user_id, limit=50):
        return self.execute("""
            SELECT id, query, engine, results_clicked, searched_at
            FROM searches WHERE user_id = %s
            ORDER BY searched_at DESC LIMIT %s
        """, (user_id, limit))

    def get_keyword_frequency(self, user_id, limit=50):
        """Uses the search_keyword_frequency view (splits queries word by word)."""
        return self.execute("""
            SELECT keyword, frequency, last_searched
            FROM search_keyword_frequency
            WHERE user_id = %s ORDER BY frequency DESC LIMIT %s
        """, (user_id, limit))

    def get_engine_stats(self, user_id):
        return self.execute("""
            SELECT engine, COUNT(*) AS total_searches,
                   AVG(results_clicked) AS avg_clicks,
                   MAX(searched_at) AS last_used
            FROM searches WHERE user_id = %s
            GROUP BY engine ORDER BY total_searches DESC
        """, (user_id,))

    def get_daily_count(self, user_id, days=7):
        return self.execute("""
            SELECT DATE(searched_at) AS day, COUNT(*) AS searches
            FROM searches
            WHERE user_id = %s
              AND searched_at >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY day ORDER BY day
        """, (user_id, str(days)))


# ─────────────────────────────────────────
#  Social Event Model
# ─────────────────────────────────────────
class SocialModel(BaseModel):

    def create(self, user_id, platform, action, content_type=None,
               time_spent_sec=0, timestamp=None, payload=None):
        return self.commit_execute("""
            INSERT INTO social_events (user_id, platform, action, content_type,
                                       time_spent_sec, event_at, raw_payload)
            VALUES (%s, %s, %s, %s, %s, COALESCE(to_timestamp(%s), NOW()), %s)
            RETURNING id
        """, (user_id, platform, action, content_type, time_spent_sec,
              timestamp, psycopg2.extras.Json(payload or {})), returning=True)

    def get_platform_stats(self, user_id, days=7):
        return self.execute("""
            SELECT platform,
                   COUNT(*) AS events,
                   SUM(time_spent_sec) AS total_sec,
                   COUNT(*) FILTER (WHERE action = 'post')    AS posts,
                   COUNT(*) FILTER (WHERE action = 'like')    AS likes,
                   COUNT(*) FILTER (WHERE action = 'share')   AS shares,
                   COUNT(*) FILTER (WHERE action = 'comment') AS comments,
                   COUNT(*) FILTER (WHERE action = 'scroll')  AS scrolls
            FROM social_events
            WHERE user_id = %s
              AND event_at >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY platform ORDER BY total_sec DESC
        """, (user_id, str(days)))

    def get_daily_activity(self, user_id, days=7):
        return self.execute("""
            SELECT DATE(event_at) AS day, platform,
                   COUNT(*) AS events, SUM(time_spent_sec) AS total_sec
            FROM social_events
            WHERE user_id = %s
              AND event_at >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY day, platform ORDER BY day
        """, (user_id, str(days)))

    def get_recent(self, user_id, limit=50):
        return self.execute("""
            SELECT id, platform, action, content_type, time_spent_sec, event_at
            FROM social_events WHERE user_id = %s
            ORDER BY event_at DESC LIMIT %s
        """, (user_id, limit))


# ─────────────────────────────────────────
#  App Usage Model
# ─────────────────────────────────────────
class AppUsageModel(BaseModel):

    def create(self, user_id, app_name, start_ts, end_ts, payload=None):
        return self.commit_execute("""
            INSERT INTO app_usage (user_id, app_name, session_start, session_end, raw_payload)
            VALUES (%s, %s, to_timestamp(%s), to_timestamp(%s), %s)
            RETURNING id, duration_sec
        """, (user_id, app_name, start_ts, end_ts,
              psycopg2.extras.Json(payload or {})), returning=True)

    def get_top_apps(self, user_id, days=7, limit=10):
        return self.execute("""
            SELECT app_name,
                   COUNT(*) AS sessions,
                   SUM(duration_sec) AS total_sec,
                   AVG(duration_sec) AS avg_sec,
                   MAX(session_start) AS last_used
            FROM app_usage
            WHERE user_id = %s
              AND session_start >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY app_name ORDER BY total_sec DESC LIMIT %s
        """, (user_id, str(days), limit))

    def get_daily_usage(self, user_id, days=7):
        return self.execute("""
            SELECT DATE(session_start) AS day, app_name,
                   SUM(duration_sec) AS total_sec, COUNT(*) AS sessions
            FROM app_usage
            WHERE user_id = %s
              AND session_start >= NOW() - (%s || ' days')::INTERVAL
            GROUP BY day, app_name ORDER BY day
        """, (user_id, str(days)))


# ─────────────────────────────────────────
#  Audit Log Model
# ─────────────────────────────────────────
class AuditModel(BaseModel):

    def get_recent(self, user_id, limit=100):
        return self.execute("""
            SELECT table_name, operation, row_id, changed_at, old_data, new_data
            FROM audit_log WHERE user_id = %s
            ORDER BY changed_at DESC LIMIT %s
        """, (user_id, limit))
