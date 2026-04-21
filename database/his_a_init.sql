-- ============================================================
-- HIS A Database – Users / Doctor Authentication
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT        UNIQUE NOT NULL,
    full_name       TEXT,
    role            TEXT        NOT NULL DEFAULT 'doctor',
    hashed_password TEXT        NOT NULL,
    created_at      TIMESTAMP   NOT NULL DEFAULT NOW()
);

-- Seed a default admin account (password: admin1234)
INSERT INTO users (username, full_name, role, hashed_password) VALUES (
    'admin',
    'System Administrator',
    'admin',
    '$2b$12$KIX/LCDsLQwXiHJ8YZWFOuaQvEqIeJHiIDU3JJ2gBE8amM1NlDzR2'
) ON CONFLICT DO NOTHING;
