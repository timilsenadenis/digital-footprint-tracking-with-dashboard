-- ============================================================
--  triggers.sql — All PostgreSQL Triggers & Functions
--  Run this AFTER schema.sql
-- ============================================================


-- ─────────────────────────────────────────────
--  HELPER: extract domain from URL
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION extract_domain(url TEXT)
RETURNS TEXT AS $$
DECLARE
    domain TEXT;
BEGIN
    -- Remove protocol and www prefix
    domain := regexp_replace(url, '^https?://(www\.)?', '');
    -- Keep only the hostname part
    domain := split_part(domain, '/', 1);
    -- Remove port if present
    domain := split_part(domain, ':', 1);
    RETURN lower(trim(domain));
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ─────────────────────────────────────────────
--  TRIGGER 1: Auto-extract domain from URL
--  Fires: BEFORE INSERT on visits
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_visits_set_domain()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.domain IS NULL AND NEW.url IS NOT NULL THEN
        NEW.domain := extract_domain(NEW.url);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_before_visit_insert ON visits;
CREATE TRIGGER trg_before_visit_insert
    BEFORE INSERT ON visits
    FOR EACH ROW
    EXECUTE FUNCTION trg_visits_set_domain();

-- Test: INSERT INTO visits (user_id, url, ...) → domain auto-filled


-- ─────────────────────────────────────────────
--  TRIGGER 2: Auto-categorize visit by domain
--  Fires: BEFORE INSERT on visits (after domain is set)
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_visits_auto_categorize()
RETURNS TRIGGER AS $$
DECLARE
    cat_id INT;
BEGIN
    IF NEW.category_id IS NULL AND NEW.domain IS NOT NULL THEN
        -- Exact match first
        SELECT category_id INTO cat_id
        FROM domain_category_map
        WHERE domain = NEW.domain
        LIMIT 1;

        -- Partial match fallback (e.g. subdomain.youtube.com → youtube.com)
        IF cat_id IS NULL THEN
            SELECT category_id INTO cat_id
            FROM domain_category_map
            WHERE NEW.domain ILIKE '%' || domain
            LIMIT 1;
        END IF;

        -- Default to 'Other' category
        IF cat_id IS NULL THEN
            SELECT id INTO cat_id FROM categories WHERE name = 'Other';
        END IF;

        NEW.category_id := cat_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_after_domain_set ON visits;
CREATE TRIGGER trg_after_domain_set
    BEFORE INSERT ON visits
    FOR EACH ROW
    EXECUTE FUNCTION trg_visits_auto_categorize();

-- Test: INSERT with url='https://youtube.com/watch?v=abc' → category='Entertainment'


-- ─────────────────────────────────────────────
--  TRIGGER 3: Audit log for social_events
--  Fires: AFTER INSERT, UPDATE, DELETE on social_events
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_audit_social()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (
        table_name, operation, row_id, user_id, old_data, new_data
    ) VALUES (
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

DROP TRIGGER IF EXISTS trg_social_audit ON social_events;
CREATE TRIGGER trg_social_audit
    AFTER INSERT OR UPDATE OR DELETE ON social_events
    FOR EACH ROW
    EXECUTE FUNCTION trg_audit_social();

-- Test: INSERT INTO social_events (...) → row appears in audit_log


-- ─────────────────────────────────────────────
--  TRIGGER 4: Update users.last_active on any activity
--  Fires: AFTER INSERT on visits, searches, social_events, app_usage
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_update_last_active()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users SET last_active = NOW() WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_visits_last_active    ON visits;
DROP TRIGGER IF EXISTS trg_searches_last_active  ON searches;
DROP TRIGGER IF EXISTS trg_social_last_active    ON social_events;
DROP TRIGGER IF EXISTS trg_app_last_active       ON app_usage;

CREATE TRIGGER trg_visits_last_active
    AFTER INSERT ON visits
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();

CREATE TRIGGER trg_searches_last_active
    AFTER INSERT ON searches
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();

CREATE TRIGGER trg_social_last_active
    AFTER INSERT ON social_events
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();

CREATE TRIGGER trg_app_last_active
    AFTER INSERT ON app_usage
    FOR EACH ROW EXECUTE FUNCTION trg_update_last_active();


-- ─────────────────────────────────────────────
--  TRIGGER 5: Prevent duplicate visits within 3 seconds
--  Fires: BEFORE INSERT on visits (debounce rapid re-loads)
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_visits_deduplicate()
RETURNS TRIGGER AS $$
DECLARE
    recent_count INT;
BEGIN
    SELECT COUNT(*) INTO recent_count
    FROM visits
    WHERE user_id = NEW.user_id
      AND url = NEW.url
      AND visit_start >= NOW() - INTERVAL '3 seconds';

    IF recent_count > 0 THEN
        RETURN NULL;  -- Cancel the insert silently
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_visits_deduplicate ON visits;
CREATE TRIGGER trg_visits_deduplicate
    BEFORE INSERT ON visits
    FOR EACH ROW
    EXECUTE FUNCTION trg_visits_deduplicate();


-- ─────────────────────────────────────────────
--  TRIGGER 6: Auto-refresh materialized view daily
--  (manual call or pg_cron job)
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION refresh_daily_summary()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY top_domains_weekly;
END;
$$ LANGUAGE plpgsql;

-- To schedule with pg_cron (if extension available):
-- SELECT cron.schedule('refresh-materialized-views', '0 * * * *', 'SELECT refresh_daily_summary()');


-- ─────────────────────────────────────────────
--  VERIFY: List all triggers in the database
-- ─────────────────────────────────────────────
-- SELECT trigger_name, event_object_table, event_manipulation, action_timing
-- FROM information_schema.triggers
-- WHERE trigger_schema = 'public'
-- ORDER BY event_object_table, trigger_name;
