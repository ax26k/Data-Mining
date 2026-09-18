-- Query 1: Filter by portal_id using an index
EXPLAIN ANALYZE
SELECT *
FROM notices
WHERE portal_id = 'P094';

-- Query 2: Filter by published date using an index
EXPLAIN ANALYZE
SELECT *
FROM notices
WHERE published_at >= '2025-01-01';

-- Query 3: Group notices by portal
EXPLAIN ANALYZE
SELECT portal_id, COUNT(*)
FROM notices
GROUP BY portal_id;

-- Query 4: Search notice body using a sequential scan
EXPLAIN ANALYZE
SELECT notice_id, title
FROM notices
WHERE body ILIKE '%road%';