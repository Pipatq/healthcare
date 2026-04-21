-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table for JWT authentication
CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username      TEXT        UNIQUE NOT NULL,
    hashed_password TEXT      NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- Generic FHIR resource store
CREATE TABLE IF NOT EXISTS fhir_resources (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type TEXT        NOT NULL,
    patient_id    TEXT,
    data          JSONB       NOT NULL,
    created_at    TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fhir_resources_type       ON fhir_resources (resource_type);
CREATE INDEX IF NOT EXISTS idx_fhir_resources_patient_id ON fhir_resources (patient_id);
CREATE INDEX IF NOT EXISTS idx_fhir_resources_data_gin   ON fhir_resources USING GIN (data);
