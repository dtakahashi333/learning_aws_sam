-- =============================================================
-- init-db.sql
-- Runs automatically on first container start via
-- /docker-entrypoint-initdb.d/
-- =============================================================

-- ============================================================
-- chatbot_app
-- ============================================================

\set chatbot_pwd `echo "$CHATBOT_APP_PASSWORD"`

CREATE USER chatbot_app_user WITH PASSWORD :'chatbot_pwd';

CREATE DATABASE chatbot_app
    WITH OWNER      = chatbot_app_user
         ENCODING   = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8'
         TEMPLATE   = template0;

-- Restrict who can connect
REVOKE CONNECT ON DATABASE chatbot_app FROM PUBLIC;
GRANT CONNECT ON DATABASE chatbot_app TO chatbot_app_user;

\connect chatbot_app chatbot_app_user

-- Lock down default schema
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Optional but recommended: dedicated schema
CREATE SCHEMA chatbot AUTHORIZATION chatbot_app_user;
ALTER ROLE chatbot_app_user SET search_path TO chatbot;

-- Create table
CREATE TABLE chatbot.sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ
);



-- ============================================================
-- authentik
-- ============================================================

\connect postgres postgres

\set authentik_pwd `echo "$AUTHENTIK_POSTGRESQL__PASSWORD"`
CREATE USER authentik_user WITH PASSWORD :'authentik_pwd';

CREATE DATABASE authentik
    WITH OWNER      = authentik_user
         ENCODING   = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8'
         TEMPLATE   = template0;

-- Allow connection
REVOKE CONNECT ON DATABASE authentik FROM PUBLIC;
GRANT CONNECT ON DATABASE authentik TO authentik_user;

\connect authentik authentik_user

-- IMPORTANT: Authentik uses public schema
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- Allow app user to use public schema (required)
GRANT ALL ON SCHEMA public TO authentik_user;
