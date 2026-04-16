-- =============================================================
-- init-db.sql
-- Runs automatically on first container start via
-- /docker-entrypoint-initdb.d/
-- =============================================================

-- ── chatbot_app ────────────────────────────────────────────────────
\set chatbot_pwd `echo "$CHATBOT_APP_PASSWORD"`
CREATE USER chatbot_app_user WITH PASSWORD :'chatbot_pwd';

CREATE DATABASE chatbot_app
    WITH OWNER     = chatbot_app_user
         ENCODING  = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8'
         TEMPLATE  = template0;

-- Restrict public access and grant full ownership to the app user
\connect chatbot_app chatbot_app_user
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT  ALL ON SCHEMA public TO chatbot_app_user;
-- Create a table for chat messages
CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    title VARCHAR(64),
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ
);

-- ── authentik ────────────────────────────────────────────────────
\connect postgres sam_user
\set authentik_pwd `echo "$AUTHENTIK_POSTGRESQL__PASSWORD"`
CREATE USER authentik_user WITH PASSWORD :'authentik_pwd';

CREATE DATABASE authentik
    WITH OWNER     = authentik_user
         ENCODING  = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8'
         TEMPLATE  = template0;

\connect authentik authentik_user
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT  ALL ON SCHEMA public TO authentik_user;
