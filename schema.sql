CREATE TABLE IF NOT EXISTS portals (
    portal_id VARCHAR(50) PRIMARY KEY,
    portal_name TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS notices (
    notice_id VARCHAR(100) PRIMARY KEY,
    portal_id VARCHAR(50),
    published_at TIMESTAMP,
    title TEXT,
    body TEXT,
    estimated_value NUMERIC(18,2),
    closing_date DATE,
    FOREIGN KEY (portal_id) REFERENCES portals(portal_id)
);

CREATE TABLE IF NOT EXISTS notice_signatures (
    notice_id VARCHAR(100) PRIMARY KEY,
    representation TEXT NOT NULL,
    num_perm INTEGER NOT NULL,
    signature TEXT NOT NULL,
    FOREIGN KEY (notice_id) REFERENCES notices(notice_id)
);

CREATE TABLE IF NOT EXISTS retrieval_runs (
    run_id SERIAL PRIMARY KEY,
    representation TEXT NOT NULL,
    num_perm INTEGER NOT NULL,
    lsh_threshold NUMERIC(4,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS retrieval_candidates (
    run_id INTEGER REFERENCES retrieval_runs(run_id),
    query_notice_id VARCHAR(100) REFERENCES notices(notice_id),
    candidate_notice_id VARCHAR(100) REFERENCES notices(notice_id),
    estimated_similarity NUMERIC(8,6),
    PRIMARY KEY (
        run_id,
        query_notice_id,
        candidate_notice_id
    )
);

CREATE INDEX IF NOT EXISTS idx_notices_portal_id
ON notices(portal_id);

CREATE INDEX IF NOT EXISTS idx_notices_published_at
ON notices(published_at);

CREATE INDEX IF NOT EXISTS idx_notices_closing_date
ON notices(closing_date);

CREATE INDEX IF NOT EXISTS idx_candidates_query_notice
ON retrieval_candidates(query_notice_id);

CREATE INDEX IF NOT EXISTS idx_candidates_candidate_notice
ON retrieval_candidates(candidate_notice_id);