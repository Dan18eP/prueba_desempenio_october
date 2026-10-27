-- ==============================================================================
-- SismoWatch Database Initialization - Script 02: Tables, Indexes & Views
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SCHEMA RAW (Bronze Metadata & Raw Batch Log)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.earthquakes_raw_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id VARCHAR(64) UNIQUE NOT NULL,
    feed_url TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    features_count INT NOT NULL DEFAULT 0,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(32) DEFAULT 'INGESTED'
);

CREATE INDEX IF NOT EXISTS idx_raw_batches_ingested ON raw.earthquakes_raw_batches (ingested_at DESC);

-- ------------------------------------------------------------------------------
-- 2. SCHEMA STAGING (Silver Refined Layer)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.earthquakes_refined (
    id VARCHAR(64) PRIMARY KEY,
    magnitude NUMERIC(4,2),
    place VARCHAR(255) NOT NULL,
    event_time_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_time_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    depth_km NUMERIC(6,2) NOT NULL,
    tsunami_alert BOOLEAN NOT NULL DEFAULT FALSE,
    significance INT DEFAULT 0,
    review_status VARCHAR(32) DEFAULT 'automatic',
    mag_type VARCHAR(16),
    event_type VARCHAR(32) DEFAULT 'earthquake',
    usgs_url TEXT,
    quality_status VARCHAR(16) DEFAULT 'VALID',
    quality_reasons TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staging_event_time ON staging.earthquakes_refined (event_time_utc DESC);
CREATE INDEX IF NOT EXISTS idx_staging_quality_status ON staging.earthquakes_refined (quality_status);

-- ------------------------------------------------------------------------------
-- 3. SCHEMA CURATED (Gold Servicing Layer for API & AI Agent)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS curated.gold_earthquakes (
    id VARCHAR(64) PRIMARY KEY,
    magnitude NUMERIC(4,2) NOT NULL,
    place VARCHAR(255) NOT NULL,
    event_time_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_time_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    depth_km NUMERIC(6,2) NOT NULL,
    tsunami_alert BOOLEAN NOT NULL DEFAULT FALSE,
    significance INT DEFAULT 0,
    review_status VARCHAR(32) DEFAULT 'automatic',
    severity_label VARCHAR(16) NOT NULL,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_explanation TEXT,
    quality_status VARCHAR(16) DEFAULT 'VALID',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices B-Tree optimizados para consultas del Dashboard y Text-to-SQL
CREATE INDEX IF NOT EXISTS idx_gold_event_time ON curated.gold_earthquakes (event_time_utc DESC);
CREATE INDEX IF NOT EXISTS idx_gold_magnitude ON curated.gold_earthquakes (magnitude DESC);
CREATE INDEX IF NOT EXISTS idx_gold_place ON curated.gold_earthquakes USING btree (place);
CREATE INDEX IF NOT EXISTS idx_gold_tsunami ON curated.gold_earthquakes (tsunami_alert) WHERE tsunami_alert = TRUE;
CREATE INDEX IF NOT EXISTS idx_gold_severity ON curated.gold_earthquakes (severity_label);
CREATE INDEX IF NOT EXISTS idx_gold_anomaly ON curated.gold_earthquakes (is_anomaly) WHERE is_anomaly = TRUE;

-- Tabla de KPIs Horarios Agregados
CREATE TABLE IF NOT EXISTS curated.gold_hourly_kpis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hour_utc TIMESTAMP WITH TIME ZONE UNIQUE NOT NULL,
    total_events INT NOT NULL DEFAULT 0,
    max_magnitude NUMERIC(4,2) DEFAULT 0.0,
    avg_magnitude NUMERIC(4,2) DEFAULT 0.0,
    tsunami_alerts_count INT NOT NULL DEFAULT 0,
    micro_count INT NOT NULL DEFAULT 0,
    minor_count INT NOT NULL DEFAULT 0,
    moderate_count INT NOT NULL DEFAULT 0,
    strong_count INT NOT NULL DEFAULT 0,
    major_count INT NOT NULL DEFAULT 0,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gold_kpis_hour ON curated.gold_hourly_kpis (hour_utc DESC);

-- Tabla de Anomalías Sísmicas (Z-Score y Enjambres)
CREATE TABLE IF NOT EXISTS curated.gold_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    earthquake_id VARCHAR(64) REFERENCES curated.gold_earthquakes(id) ON DELETE CASCADE,
    magnitude NUMERIC(4,2) NOT NULL,
    place VARCHAR(255) NOT NULL,
    z_score NUMERIC(5,2) NOT NULL,
    is_swarm BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_explanation TEXT NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gold_anomalies_detected ON curated.gold_anomalies (detected_at DESC);

-- Tabla de Reportes Ejecutivos Generados con IA
CREATE TABLE IF NOT EXISTS curated.gold_ai_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    title VARCHAR(255) NOT NULL,
    executive_summary TEXT NOT NULL,
    verified_metrics JSONB NOT NULL,
    most_active_region VARCHAR(255),
    risk_assessment VARCHAR(32) NOT NULL,
    prompt_version VARCHAR(32) NOT NULL,
    model_used VARCHAR(64) NOT NULL,
    verified_match BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gold_reports_created ON curated.gold_ai_reports (created_at DESC);

-- ------------------------------------------------------------------------------
-- 4. SCHEMA AUDIT (Gobernanza, Trazabilidad, Usuarios & Métricas)
-- ------------------------------------------------------------------------------

-- Tabla de Resultados de Calidad de Datos (PDF Pág. 5)
CREATE TABLE IF NOT EXISTS audit.quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id VARCHAR(64) NOT NULL,
    execution_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rules_evaluated INT NOT NULL,
    rules_passed INT NOT NULL,
    rules_failed INT NOT NULL,
    quality_score NUMERIC(5,2) NOT NULL,
    freshness_lag_minutes INT NOT NULL,
    volume_count INT NOT NULL,
    status VARCHAR(16) NOT NULL,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_audit_quality_exec ON audit.quality_metrics (execution_timestamp DESC);

-- Tabla de Conciliación de Lotes (Regla "20 In -> 20 Out" - Cero Pérdida)
CREATE TABLE IF NOT EXISTS audit.batch_reconciliation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id VARCHAR(64) UNIQUE NOT NULL,
    source_feed VARCHAR(255) NOT NULL,
    raw_count INT NOT NULL,
    silver_count INT NOT NULL,
    gold_count INT NOT NULL,
    fidelity_rate NUMERIC(5,2) GENERATED ALWAYS AS (
        CASE WHEN raw_count > 0 THEN (gold_count::NUMERIC / raw_count::NUMERIC) * 100.0 ELSE 100.0 END
    ) STORED,
    loss_count INT GENERATED ALWAYS AS (raw_count - gold_count) STORED,
    reconciled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_time ON audit.batch_reconciliation (reconciled_at DESC);

-- Tabla de Registro de Ejecuciones de IA (PDF Pág. 5)
CREATE TABLE IF NOT EXISTS audit.ai_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name VARCHAR(64) NOT NULL,
    prompt_version VARCHAR(32) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    latency_ms INT NOT NULL,
    estimated_cost_usd NUMERIC(8,6) DEFAULT 0.0,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(16) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_exec_time ON audit.ai_executions (executed_at DESC);

-- Tabla de Alertas de Fallos en Pipeline (PDF Pág. 4)
CREATE TABLE IF NOT EXISTS audit.pipeline_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dag_id VARCHAR(64) NOT NULL,
    task_id VARCHAR(64) NOT NULL,
    execution_date TIMESTAMP WITH TIME ZONE NOT NULL,
    error_message TEXT NOT NULL,
    alert_channel VARCHAR(32) DEFAULT 'INTERNAL_AUDIT',
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_alerts_date ON audit.pipeline_alerts (execution_date DESC);

-- Tabla de Usuarios y Roles RBAC (PDF Pág. 2 y 3)
CREATE TABLE IF NOT EXISTS audit.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(128) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(16) NOT NULL CHECK (role IN ('viewer', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON audit.users (username);

-- ------------------------------------------------------------------------------
-- 5. VISTA DE CUARENTENA DE AUDITORÍA (Endpoint Admin GET /api/quality/quarantine)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW curated.quality_quarantine AS
SELECT 
    id,
    magnitude,
    place,
    event_time_utc,
    longitude,
    latitude,
    depth_km,
    quality_status,
    quality_reasons,
    processed_at
FROM staging.earthquakes_refined
WHERE quality_status = 'FLAGGED';
