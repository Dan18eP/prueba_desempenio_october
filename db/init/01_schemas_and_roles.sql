-- ==============================================================================
-- SismoWatch Database Initialization - Script 01: Schemas & Roles
-- ==============================================================================

-- Enable required cryptographic and UUID extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Create Core Medallion Schemas & Governance Schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;
CREATE SCHEMA IF NOT EXISTS audit;

-- 2. Create Distinct Roles (Principio de Mínimo Privilegio - PDF Pág. 5)

-- A. Ingestion Role (Airflow Ingest DAG)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_ingest') THEN
        CREATE ROLE sismo_ingest WITH LOGIN PASSWORD 'ingest_secret_pass_2026';
    END IF;
END $$;

-- B. Transformation Role (PySpark / Airflow Processing)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_transform') THEN
        CREATE ROLE sismo_transform WITH LOGIN PASSWORD 'transform_secret_pass_2026';
    END IF;
END $$;

-- C. Application Read-Only Role (FastAPI Backend & Chatbot)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sismo_app_readonly') THEN
        CREATE ROLE sismo_app_readonly WITH LOGIN PASSWORD 'readonly_app_secret_2026';
    END IF;
END $$;

-- 3. Assign Least-Privilege Permissions

-- Permisos para sismo_ingest: Acceso a raw y audit
GRANT USAGE ON SCHEMA raw, audit TO sismo_ingest;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw TO sismo_ingest;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw TO sismo_ingest;
GRANT INSERT, SELECT, UPDATE ON ALL TABLES IN SCHEMA audit TO sismo_ingest;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO sismo_ingest;

-- Permisos para sismo_transform: Acceso completo a raw, staging, curated y audit
GRANT USAGE ON SCHEMA raw, staging, curated, audit TO sismo_transform;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw, staging, curated, audit TO sismo_transform;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA raw, staging, curated, audit TO sismo_transform;

-- Permisos para sismo_app_readonly: Exclusivamente SELECT sobre curated y tablas públicas de audit
GRANT USAGE ON SCHEMA curated, audit TO sismo_app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO sismo_app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO sismo_app_readonly;

-- 4. Set Default Privileges for Future Tables
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL ON TABLES TO sismo_ingest;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL ON TABLES TO sismo_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT ALL ON TABLES TO sismo_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT ALL ON TABLES TO sismo_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO sismo_app_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON TABLES TO sismo_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT ON TABLES TO sismo_app_readonly;
