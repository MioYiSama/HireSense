DROP TABLE "user";
CREATE TYPE user_job AS ENUM ('frontend', 'backend');
CREATE TABLE IF NOT EXISTS "user"
(
    id              UUID     NOT NULL DEFAULT gen_random_uuid(),
    name            TEXT     NOT NULL,
    account         TEXT     NOT NULL,
    password        TEXT     NOT NULL,
    job             USER_JOB NOT NULL DEFAULT 'frontend',
    resume          TEXT              DEFAULT NULL,
    personalization TEXT              DEFAULT NULL,

    PRIMARY KEY (id),
    UNIQUE (account)
);

DROP TABLE interview;
CREATE TYPE interview_status AS ENUM ('started', 'stopped');
CREATE TABLE IF NOT EXISTS interview
(
    id         UUID             NOT NULL DEFAULT gen_random_uuid(),
    status     INTERVIEW_STATUS NOT NULL DEFAULT 'started',
    created_at TIMESTAMPTZ      NOT NULL DEFAULT now(),
    report     JSONB                     DEFAULT NULL,
    user_id    UUID             NOT NULL,

    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES "user" (id) ON DELETE CASCADE
);