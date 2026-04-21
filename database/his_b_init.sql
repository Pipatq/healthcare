-- ============================================================
-- HIS B Legacy Database – Simulated Legacy Hospital System
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Legacy Patient Table (non-FHIR format – HIS B internal schema)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    hn          TEXT        PRIMARY KEY,          -- Hospital Number
    first_name  TEXT        NOT NULL,
    last_name   TEXT        NOT NULL,
    gender      TEXT,                             -- 'M', 'F', 'U'
    dob         DATE,
    phone       TEXT,
    address     TEXT,
    id_card     TEXT,
    blood_type  TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Legacy Observation Table (lab results, vital signs, etc.)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    id          SERIAL      PRIMARY KEY,
    patient_hn  TEXT        NOT NULL REFERENCES patients(hn),
    loinc_code  TEXT        NOT NULL,
    display     TEXT,
    value       TEXT,
    unit        TEXT,
    status      TEXT        NOT NULL DEFAULT 'final',
    issued_at   TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Legacy Service Request Table (lab orders)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS service_requests (
    id              SERIAL  PRIMARY KEY,
    patient_hn      TEXT    NOT NULL REFERENCES patients(hn),
    order_code      TEXT    NOT NULL,
    display         TEXT,
    priority        TEXT    NOT NULL DEFAULT 'routine',
    status          TEXT    NOT NULL DEFAULT 'active',
    requested_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- API Keys for authenticating the FHIR Gateway
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    key_hash    TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ===========================================================================
-- Seed Data
-- ===========================================================================
INSERT INTO patients (hn, first_name, last_name, gender, dob, phone, address, id_card, blood_type) VALUES
    ('HN-0001', 'สมชาย',   'ใจดี',    'M', '1980-05-15', '0812345678', '123 ถนนสุขุมวิท กรุงเทพมหานคร 10110', '1234567890123', 'A+'),
    ('HN-0002', 'สมหญิง',  'รักดี',   'F', '1990-08-22', '0898765432', '456 ถนนพระราม 4 กรุงเทพมหานคร 10330', '9876543210123', 'B+'),
    ('HN-0003', 'วิชัย',   'แสงทอง',  'M', '1975-03-10', '0871234567', '789 ถนนลาดพร้าว กรุงเทพมหานคร 10230', '1357924680135', 'O+'),
    ('HN-0004', 'นภาพร',   'จันทร์งาม','F', '2000-12-01', '0853698741', '321 ถนนเพชรบุรี กรุงเทพมหานคร 10400', '2468013579246', 'AB+'),
    ('HN-0005', 'ประยุทธ์', 'สุขใจ',   'M', '1968-07-04', '0819876543', '654 ถนนรัชดาภิเษก กรุงเทพมหานคร 10900', '1122334455667', 'A-')
ON CONFLICT DO NOTHING;

INSERT INTO observations (patient_hn, loinc_code, display, value, unit, status) VALUES
    ('HN-0001', '2160-0',  'Creatinine [Mass/volume] in Serum or Plasma',    '0.9',  'mg/dL', 'final'),
    ('HN-0001', '17861-6', 'Calcium [Mass/volume] in Serum or Plasma',        '9.5',  'mg/dL', 'final'),
    ('HN-0001', '2823-3',  'Potassium [Moles/volume] in Serum or Plasma',     '4.1',  'mmol/L','final'),
    ('HN-0002', '718-7',   'Hemoglobin [Mass/volume] in Blood',               '13.2', 'g/dL',  'final'),
    ('HN-0002', '4548-4',  'Hemoglobin A1c/Hemoglobin.total in Blood',        '6.8',  '%',     'final'),
    ('HN-0003', '2160-0',  'Creatinine [Mass/volume] in Serum or Plasma',     '1.1',  'mg/dL', 'final'),
    ('HN-0003', '3094-0',  'Urea nitrogen [Mass/volume] in Serum or Plasma',  '18.0', 'mg/dL', 'final'),
    ('HN-0004', '2093-3',  'Cholesterol [Mass/volume] in Serum or Plasma',    '195',  'mg/dL', 'final'),
    ('HN-0005', '55284-4', 'Blood pressure panel with all children optional',  '130',  'mmHg',  'final'),
    ('HN-0005', '8867-4',  'Heart rate',                                       '78',   '/min',  'final')
ON CONFLICT DO NOTHING;

INSERT INTO service_requests (patient_hn, order_code, display, priority, status) VALUES
    ('HN-0001', 'CHEM-001', 'Comprehensive Metabolic Panel',    'routine', 'active'),
    ('HN-0001', 'RENAL-001','Renal Function Panel',             'routine', 'completed'),
    ('HN-0002', 'CBC-001',  'Complete Blood Count',             'urgent',  'completed'),
    ('HN-0002', 'HBA1C-001','Hemoglobin A1c',                   'routine', 'active'),
    ('HN-0003', 'RENAL-001','Renal Function Panel',             'routine', 'active'),
    ('HN-0004', 'LIPID-001','Lipid Panel',                      'routine', 'active'),
    ('HN-0005', 'CARD-001', 'Cardiac Risk Assessment',          'urgent',  'active')
ON CONFLICT DO NOTHING;
