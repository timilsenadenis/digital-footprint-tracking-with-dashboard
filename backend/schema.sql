-- ============================================================
--  Digital Footprint Tracker — PostgreSQL Schema
--  Tables: users, visits, searches, social_events, app_usage
--  Features: triggers, materialized views, RLS, partitioning
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- fuzzy search on URLs

-- ─────────────────────────────────────────────
--  LOOKUP: categories
-- ─────────────────────────────────────────────
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    color_hex   VARCHAR(7) DEFAULT '#888888'
);

INSERT INTO categories (name, color_hex) VALUES
    ('Social Media',    '#4267B2'),
    ('Search',          '#34A853'),
    ('Entertainment',   '#FF0000'),
    ('News',            '#FF6600'),
    ('Shopping',        '#FF9900'),
    ('Education',       '#0057E7'),
    ('Productivity',    '#7B68EE'),
    ('Technology',      '#00BFFF'),
    ('Finance',         '#2E8B57'),
    ('Other',           '#888888');

-- ─────────────────────────────────────────────
--  LOOKUP: domain_category_map
-- ─────────────────────────────────────────────
CREATE TABLE domain_category_map (
    domain      VARCHAR(100) PRIMARY KEY,
    category_id INT REFERENCES categories(id)
);

INSERT INTO domain_category_map (domain, category_id) VALUES
    ('facebook.com',    1), ('instagram.com',  1), ('twitter.com',  1),
    ('x.com',           1), ('linkedin.com',   1), ('tiktok.com',   1),
    ('reddit.com',      1), ('snapchat.com',   1), ('pinterest.com',1),
    ('google.com',      2), ('bing.com',       2), ('duckduckgo.com',2),
    ('youtube.com',     3), ('netflix.com',    3), ('twitch.tv',    3),
    ('spotify.com',     3), ('primevideo.com', 3),
    ('bbc.com',         4), ('cnn.com',        4), ('reuters.com',  4),
    ('amazon.com',      5), ('ebay.com',       5), ('flipkart.com', 5),
    ('coursera.org',    6), ('udemy.com',      6), ('wikipedia.org',6),
    ('khanacademy.org', 6), ('stackoverflow.com',7),
    ('github.com',      7), ('notion.so',      7), ('docs.google.com',7),
    ('gmail.com',       7), ('outlook.com',    7),
    ('dev.to',          8), ('medium.com',     8),
    ('paypal.com',      9), ('bankofamerica.com',9);

-- ─────────────────────────────────────────────
--  USERS
-- ─────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    api_key         UUID UNIQUE DEFAULT uuid_generate_v4(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_active     TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────
--  VISITS (partitioned by month)
-- ─────────────────────────────────────────────
CREATE TABLE visits (
    id              BIGSERIAL,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    domain          VARCHAR(200),
    page_title      TEXT,
    category_id     INT REFERENCES categories(id),
    visit_start     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    visit_end       TIMESTAMPTZ,
    duration_sec    INT GENERATED ALWAYS AS (
                        EXTRACT(EPOCH FROM (visit_end - visit_start))::INT
                    ) STORED,
    device_type     VARCHAR(20) DEFAULT 'desktop',
    browser         VARCHAR(50),
    is_incognito    BOOLEAN DEFAULT FALSE,
    raw_payload     JSONB,
    PRIMARY KEY (id, visit_start)
) PARTITION BY RANGE (visit_start);

-- Create partitions for current and next 3 months
CREATE TABLE visits_2025_01 PARTITION OF visits
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE visits_2025_02 PARTITION OF visits
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE visits_2025_03 PARTITION OF visits
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE visits_2025_04 PARTITION OF visits
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE visits_2025_05 PARTITION OF visits
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE visits_2025_06 PARTITION OF visits
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE visits_default  PARTITION OF visits DEFAULT;

-- Indexes on visits
CREATE INDEX idx_visits_user_id    ON visits (user_id);
CREATE INDEX idx_visits_domain     ON visits (domain);
CREATE INDEX idx_visits_category   ON visits (category_id);
CREATE INDEX idx_visits_start      ON visits (visit_start DESC);
CREATE INDEX idx_visits_url_trgm   ON visits USING GIN (url gin_trgm_ops);

-- ─────────────────────────────────────────────
--  SEARCHES
-- ─────────────────────────────────────────────
CREATE TABLE searches (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query           TEXT NOT NULL,
    engine          VARCHAR(30) DEFAULT 'google',
    results_clicked INT DEFAULT 0,
    searched_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload     JSONB
);

CREATE INDEX idx_searches_user_id   ON searches (user_id);
CREATE INDEX idx_searches_engine    ON searches (engine);
CREATE INDEX idx_searches_at        ON searches (searched_at DESC);
CREATE INDEX idx_searches_query_trgm ON searches USING GIN (query gin_trgm_ops);

-- ─────────────────────────────────────────────
--  SOCIAL EVENTS
-- ─────────────────────────────────────────────
CREATE TABLE social_events (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform        VARCHAR(50) NOT NULL,
    action          VARCHAR(50) NOT NULL,  -- 'post','like','share','comment','scroll'
    content_type    VARCHAR(30),           -- 'video','image','text','story'
    time_spent_sec  INT DEFAULT 0,
    event_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload     JSONB
);

CREATE INDEX idx_social_user_id   ON social_events (user_id);
CREATE INDEX idx_social_platform  ON social_events (platform);
CREATE INDEX idx_social_action    ON social_events (action);
CREATE INDEX idx_social_at        ON social_events (event_at DESC);

-- ─────────────────────────────────────────────
--  APP USAGE
-- ─────────────────────────────────────────────
CREATE TABLE app_usage (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    app_name        VARCHAR(100) NOT NULL,
    category_id     INT REFERENCES categories(id),
    session_start   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_end     TIMESTAMPTZ,
    duration_sec    INT GENERATED ALWAYS AS (
                        EXTRACT(EPOCH FROM (session_end - session_start))::INT
                    ) STORED,
    raw_payload     JSONB
);

CREATE INDEX idx_app_usage_user_id ON app_usage (user_id);
CREATE INDEX idx_app_usage_app     ON app_usage (app_name);
CREATE INDEX idx_app_usage_start   ON app_usage (session_start DESC);

-- ─────────────────────────────────────────────
--  AUDIT LOG (trigger-populated)
-- ─────────────────────────────────────────────
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(50),
    operation   VARCHAR(10),  -- INSERT / UPDATE / DELETE
    row_id      BIGINT,
    user_id     UUID,
    changed_at  TIMESTAMPTZ DEFAULT NOW(),
    old_data    JSONB,
    new_data    JSONB
);

-- ─────────────────────────────────────────────
--  TRIGGER 1: auto-populate domain from URL
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION extract_domain(url TEXT)
RETURNS TEXT AS $$
DECLARE
    domain TEXT;
BEGIN
    domain := regexp_replace(url, '^https?://(www\.)?', '');
    domain := split_part(domain, '/', 1);
    RETURN lower(domain);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION trg_visits_set_domain()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.domain IS NULL AND NEW.url IS NOT NULL THEN
        NEW.domain := extract_domain(NEW.url);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_before_visit_insert
    BEFORE INSERT ON visits
    FOR EACH ROW EXECUTE FUNCTION trg_visits_set_domain();

-- ─────────────────────────────────────────────
--  TRIGGER 2: auto-categorize visit by domain
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_visits_auto_categorize()
RETURNS TRIGGER AS $$
DECLARE
    cat_id INT;
BEGIN
    IF NEW.category_id IS NULL THEN
        SELECT category_id INTO cat_id
        FROM domain_category_map
        WHERE NEW.domain ILIKE '%' || domain
        LIMIT 1;

        NEW.category_id := COALESCE(cat_id,
            (SELECT id FROM categories WHERE name = 'Other'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_domain_set
    BEFORE INSERT ON visits
    FOR EACH ROW EXECUTE FUNCTION trg_visits_auto_categorize();

-- ─────────────────────────────────────────────
--  TRIGGER 3: audit log on social_events
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_audit_social()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, operation, row_id, user_id, old_data, new_data)
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        COALESCE(NEW.id, OLD.id),
        COALESCE(NEW.user_id, OLD.user_id),
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::JSONB ELSE NULL END,
        CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW)::JSONB ELSE NULL END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_social_audit
    AFTER INSERT OR UPDATE OR DELETE ON social_events
    FOR EACH ROW EXECUTE FUNCTION trg_audit_social();

-- ─────────────────────────────────────────────
--  TRIGGER 4: update users.last_active on any insert
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_update_last_active()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users SET last_active = NOW() WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_visits_last_active
    AFTER INSERT ON visits
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();

CREATE TRIGGER trg_searches_last_active
    AFTER INSERT ON searches
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();

-- ─────────────────────────────────────────────
--  MATERIALIZED VIEW: daily_summary
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW daily_summary AS
SELECT
    v.user_id,
    DATE(v.visit_start)                         AS day,
    COUNT(*)                                    AS total_visits,
    COUNT(DISTINCT v.domain)                    AS unique_domains,
    SUM(v.duration_sec)                         AS total_time_sec,
    AVG(v.duration_sec)                         AS avg_time_per_visit,
    MAX(v.duration_sec)                         AS longest_visit_sec,
    COUNT(*) FILTER (WHERE c.name = 'Social Media') AS social_visits,
    COUNT(*) FILTER (WHERE c.name = 'Entertainment') AS entertainment_visits,
    COUNT(*) FILTER (WHERE c.name = 'Productivity')  AS productivity_visits
FROM visits v
LEFT JOIN categories c ON v.category_id = c.id
GROUP BY v.user_id, DATE(v.visit_start)
WITH DATA;

CREATE UNIQUE INDEX idx_daily_summary ON daily_summary (user_id, day);

-- Refresh command (run via cron or pg_cron):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY daily_summary;

-- ─────────────────────────────────────────────
--  MATERIALIZED VIEW: top_domains_weekly
-- ─────────────────────────────────────────────
CREATE MATERIALIZED VIEW top_domains_weekly AS
SELECT
    user_id,
    DATE_TRUNC('week', visit_start)             AS week_start,
    domain,
    COUNT(*)                                    AS visit_count,
    SUM(duration_sec)                           AS total_sec,
    RANK() OVER (
        PARTITION BY user_id, DATE_TRUNC('week', visit_start)
        ORDER BY COUNT(*) DESC
    )                                           AS rank_by_visits
FROM visits
WHERE domain IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', visit_start), domain
WITH DATA;

CREATE INDEX idx_top_domains_weekly ON top_domains_weekly (user_id, week_start);

-- ─────────────────────────────────────────────
--  VIEW: hourly_activity_heatmap
-- ─────────────────────────────────────────────
CREATE VIEW hourly_activity_heatmap AS
SELECT
    user_id,
    EXTRACT(DOW  FROM visit_start)::INT         AS day_of_week,   -- 0=Sun
    EXTRACT(HOUR FROM visit_start)::INT         AS hour_of_day,
    COUNT(*)                                    AS visit_count,
    SUM(duration_sec)                           AS total_sec
FROM visits
GROUP BY user_id, day_of_week, hour_of_day;

-- ─────────────────────────────────────────────
--  VIEW: search_keyword_frequency
-- ─────────────────────────────────────────────
CREATE VIEW search_keyword_frequency AS
SELECT
    user_id,
    lower(trim(word))                           AS keyword,
    COUNT(*)                                    AS frequency,
    MAX(searched_at)                            AS last_searched
FROM searches,
     unnest(string_to_array(query, ' ')) AS word
WHERE length(trim(word)) > 2
GROUP BY user_id, lower(trim(word))
ORDER BY frequency DESC;

-- ─────────────────────────────────────────────
--  ROW-LEVEL SECURITY
-- ─────────────────────────────────────────────
ALTER TABLE visits       ENABLE ROW LEVEL SECURITY;
ALTER TABLE searches     ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_usage    ENABLE ROW LEVEL SECURITY;

-- Policy: users see only their own rows
CREATE POLICY user_visits_policy ON visits
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY user_searches_policy ON searches
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY user_social_policy ON social_events
    USING (user_id = current_setting('app.current_user_id')::UUID);

CREATE POLICY user_app_usage_policy ON app_usage
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- ─────────────────────────────────────────────
--  WINDOW FUNCTION QUERY EXAMPLES
-- ─────────────────────────────────────────────

-- Example 1: Time gap between consecutive visits (useful for session detection)
-- SELECT
--     id, domain, visit_start,
--     LAG(visit_start) OVER (PARTITION BY user_id ORDER BY visit_start) AS prev_visit,
--     EXTRACT(EPOCH FROM (visit_start - LAG(visit_start) OVER
--         (PARTITION BY user_id ORDER BY visit_start))) / 60 AS gap_minutes
-- FROM visits WHERE user_id = $1;

-- Example 2: Cumulative time per category per day
-- SELECT
--     DATE(visit_start) AS day,
--     c.name AS category,
--     SUM(duration_sec) AS daily_sec,
--     SUM(SUM(duration_sec)) OVER
--         (PARTITION BY c.name ORDER BY DATE(visit_start)) AS running_total_sec
-- FROM visits v JOIN categories c ON v.category_id = c.id
-- WHERE v.user_id = $1
-- GROUP BY day, c.name;