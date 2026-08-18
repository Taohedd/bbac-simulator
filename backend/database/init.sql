-- ============================================================
-- BBAC Simulator — Database Initialization Script
-- Run once against a fresh PostgreSQL 15+ database that has
-- the TimescaleDB extension installed on the server.
-- ============================================================

-- Enable TimescaleDB (must be first)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(255) NOT NULL UNIQUE,
    email       VARCHAR(255) NOT NULL UNIQUE,
    role        VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ============================================================
-- ACTIVITY LOGS  (TimescaleDB Hypertable)
-- NOTE: Foreign keys cannot point INTO a hypertable in
-- TimescaleDB. Referential integrity for log_id in risk_scores
-- and risk_score_id in access_decisions is enforced at the
-- application layer (analytics engine + enforcement module).
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_logs (
    id                  UUID         NOT NULL DEFAULT gen_random_uuid(),
    user_id             UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    timestamp           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    action              VARCHAR(100) NOT NULL,
    ip_address          INET,
    location            VARCHAR(255),
    device_fingerprint  VARCHAR(255),
    resource_accessed   VARCHAR(255),
    session_id          UUID,
    PRIMARY KEY (id, timestamp)  -- composite PK required by TimescaleDB
);

SELECT create_hypertable('activity_logs', 'timestamp', if_not_exists => TRUE);

-- Composite index covers "all logs for user X in time range" queries
CREATE INDEX IF NOT EXISTS ix_activity_logs_user_time
    ON activity_logs(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_activity_logs_session_id
    ON activity_logs(session_id);

-- ============================================================
-- RISK SCORES  (TimescaleDB Hypertable)
-- log_id references activity_logs but FK is omitted —
-- see note above about TimescaleDB hypertable FK limitation.
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_scores (
    id           UUID    NOT NULL DEFAULT gen_random_uuid(),
    user_id      UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_id       UUID    NOT NULL,  -- FK enforced at application layer
    score        FLOAT   NOT NULL CHECK (score >= 0 AND score <= 100),
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    features_json JSONB,
    PRIMARY KEY (id, computed_at)  -- composite PK required by TimescaleDB
);

SELECT create_hypertable('risk_scores', 'computed_at', if_not_exists => TRUE);

-- Composite index covers "latest scores for user X" queries
CREATE INDEX IF NOT EXISTS ix_risk_scores_user_time
    ON risk_scores(user_id, computed_at DESC);

CREATE INDEX IF NOT EXISTS ix_risk_scores_log_id
    ON risk_scores(log_id);

-- ============================================================
-- ACCESS DECISIONS
-- risk_score_id references risk_scores (hypertable) —
-- FK omitted; enforced at application layer.
-- ============================================================
CREATE TABLE IF NOT EXISTS access_decisions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    risk_score_id  UUID        NOT NULL,  -- FK enforced at application layer
    decision       VARCHAR(50) NOT NULL
                   CHECK (decision IN ('ALLOW', 'MFA_CHALLENGE', 'BLOCK')),
    reason         TEXT,
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_access_decisions_user_id
    ON access_decisions(user_id);

CREATE INDEX IF NOT EXISTS ix_access_decisions_decided_at
    ON access_decisions(decided_at DESC);

-- ============================================================
-- POLICIES
-- ============================================================
CREATE TABLE IF NOT EXISTS policies (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL UNIQUE,  -- UNIQUE enables ON CONFLICT below
    low_threshold   FLOAT        NOT NULL CHECK (low_threshold >= 0),
    high_threshold  FLOAT        NOT NULL CHECK (high_threshold <= 100),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_thresholds CHECK (low_threshold < high_threshold)
);

-- Seed the default policy (ON CONFLICT works because name is UNIQUE)
INSERT INTO policies (name, low_threshold, high_threshold, is_active)
VALUES ('Default BBAC Policy', 30.0, 70.0, TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- USER BASELINES
-- ============================================================
CREATE TABLE IF NOT EXISTS user_baselines (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID         NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    avg_login_hour       FLOAT,
    common_subnet        VARCHAR(255),
    common_device        VARCHAR(255),
    typical_actions_json JSONB,
    updated_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- USER SESSIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at    TIMESTAMPTZ,
    status      VARCHAR(50) NOT NULL
                CHECK (status IN ('ACTIVE', 'EXPIRED', 'TERMINATED'))
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id
    ON user_sessions(user_id);

CREATE INDEX IF NOT EXISTS ix_user_sessions_status
    ON user_sessions(status);