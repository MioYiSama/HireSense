DO $$
BEGIN
    CREATE TYPE user_job AS ENUM ('frontend', 'backend');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'user');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE interview_status AS ENUM ('started', 'stopped');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

DO $$
BEGIN
    CREATE TYPE interview_mode AS ENUM ('single', 'panel_trio');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS "user"
(
    id              UUID      NOT NULL,
    name            TEXT      NOT NULL,
    account         TEXT      NOT NULL,
    password        TEXT      NOT NULL,
    token           TEXT      NULL     DEFAULT NULL,
    role            USER_ROLE NOT NULL DEFAULT 'user',
    job             USER_JOB  NOT NULL DEFAULT 'frontend',
    resume          TEXT      NULL     DEFAULT NULL,
    personalization TEXT      NULL     DEFAULT NULL,

    PRIMARY KEY (id),
    UNIQUE (account)
);

CREATE TABLE IF NOT EXISTS auth_token
(
    id         UUID        NOT NULL,
    token_id   UUID        NOT NULL,
    user_id    UUID        NOT NULL,
    token_hash TEXT        NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL     DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (id),
    UNIQUE (token_id),
    UNIQUE (token_hash),
    FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auth_token_user_id
    ON auth_token (user_id);

CREATE INDEX IF NOT EXISTS idx_auth_token_lookup
    ON auth_token (user_id, token_id, token_hash);

CREATE TABLE IF NOT EXISTS interview
(
    id         UUID             NOT NULL,
    mode       INTERVIEW_MODE   NOT NULL DEFAULT 'single',
    status     INTERVIEW_STATUS NOT NULL DEFAULT 'started',
    created_at TIMESTAMPTZ      NOT NULL DEFAULT now(),
    report     JSONB            NULL     DEFAULT NULL,
    user_id    UUID             NOT NULL,

    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_user_id_created_at
    ON interview (user_id, created_at DESC);

ALTER TABLE interview
    ADD COLUMN IF NOT EXISTS mode INTERVIEW_MODE NOT NULL DEFAULT 'single';
