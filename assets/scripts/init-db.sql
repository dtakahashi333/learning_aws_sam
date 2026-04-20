-- =============================================================
-- init-db.sql
-- Runs automatically on first container start via
-- /docker-entrypoint-initdb.d/
-- =============================================================

-- ============================================================
-- chatbot_app
-- ============================================================

\set chatbot_pwd `echo "$CHATBOT_APP_PASSWORD"`

-- 1. Setup Variables (Run in psql)
\set chatbot_pwd `echo "$CHATBOT_APP_PASSWORD"`

-- 2. Create Roles
-- The Owner: Controls structure, cannot log in (Security layer)
CREATE ROLE chatbot_app_owner NOLOGIN;
-- The App User: Used by the application code to log in
CREATE USER chatbot_app_user WITH PASSWORD :'chatbot_pwd';

-- 3. Create Database
-- We use template1 (standard) because template0 is often superuser-only
CREATE DATABASE chatbot_app
    WITH OWNER      = chatbot_app_owner
         ENCODING   = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8';

-- 4. Database-Level Security
REVOKE CONNECT ON DATABASE chatbot_app FROM PUBLIC;
GRANT CONNECT ON DATABASE chatbot_app TO chatbot_app_user;

-- 5. Switch context to the new database as Superuser/Admin
\connect chatbot_app postgres

-- 6. Schema Security
-- Remove public access and create a dedicated namespace
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA chatbot AUTHORIZATION chatbot_app_owner;

-- 7. Grant Data Permissions (The "Best Practice" Set)
-- Allow the app user to see and enter the schema
GRANT USAGE ON SCHEMA chatbot TO chatbot_app_user;

-- Allow the app user to perform DML (Data) but not DDL (Structure)
-- We grant this to all current and FUTURE tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA chatbot TO chatbot_app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA chatbot TO chatbot_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA chatbot 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO chatbot_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA chatbot 
    GRANT USAGE, SELECT ON SEQUENCES TO chatbot_app_user;

-- 8. Configuration
ALTER ROLE chatbot_app_user SET search_path TO chatbot;

-- 9. Create Table (Performed by Admin/Owner context)
-- Since we are connected as postgres, we can create this for the owner
CREATE TABLE chatbot.sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ
);

-- Ensure ownership is correct
ALTER TABLE chatbot.sessions OWNER TO chatbot_app_owner;



-- ============================================================
-- authentik
-- ============================================================

\connect postgres postgres

\set authentik_pwd `echo "$AUTHENTIK_POSTGRESQL__PASSWORD"`

-- Create the user
CREATE USER authentik_user WITH PASSWORD :'authentik_pwd';

-- Create database (using template1 for better compatibility)
CREATE DATABASE authentik
    WITH OWNER      = authentik_user
         ENCODING   = 'UTF8'
         LC_COLLATE = 'en_US.utf8'
         LC_CTYPE   = 'en_US.utf8'
         TEMPLATE   = template1;

-- Lock down connection
REVOKE CONNECT ON DATABASE authentik FROM PUBLIC;
GRANT CONNECT ON DATABASE authentik TO authentik_user;

-- Connect to target DB to fix schema permissions
\connect authentik postgres

-- Ensure authentik_user owns the public schema so it can run migrations
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO authentik_user;
GRANT ALL ON SCHEMA public TO authentik_user;
