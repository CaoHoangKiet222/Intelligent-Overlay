VECTOR_SQL = """
SELECT s.id,
       s.document_id,
       s.text,
       s.start_offset,
       s.end_offset,
       s.page_no,
       s.paragraph_no,
       s.sentence_no,
       1 - (e.vector <=> :qvec) AS vscore
FROM embeddings e
JOIN segments s ON s.id = e.segment_id
WHERE s.document_id = :document_id
  AND e.dim = :query_dim
ORDER BY e.vector <=> :qvec
LIMIT :limit
"""


LEXICAL_SQL = """
SELECT s.id,
       s.document_id,
       s.text,
       s.start_offset,
       s.end_offset,
       s.page_no,
       s.paragraph_no,
       s.sentence_no,
       similarity(s.text, :query) AS tscore
FROM segments s
WHERE s.document_id = :document_id
  AND s.text % :query
ORDER BY tscore DESC
LIMIT :limit
"""


HYBRID_SQL = """
WITH q AS (
  SELECT CAST(:query AS text) AS qstr, CAST(:alpha AS double precision) AS alpha
),
vec AS (
  SELECT s.id AS segment_id,
         1 - (e.vector <=> :qvec) AS vscore
  FROM embeddings e
  JOIN segments s ON s.id = e.segment_id
  WHERE s.document_id = :document_id
    AND e.dim = :query_dim
  ORDER BY e.vector <=> :qvec
  LIMIT :vec_k
),
trgm AS (
  SELECT s.id AS segment_id,
         similarity(s.text, (SELECT qstr FROM q)) AS tscore
  FROM segments s
  WHERE s.document_id = :document_id
    AND s.text % (SELECT qstr FROM q)
  ORDER BY tscore DESC
  LIMIT :trgm_k
),
mix AS (
  SELECT COALESCE(v.segment_id, t.segment_id) AS segment_id,
         COALESCE(v.vscore, 0) AS vscore,
         COALESCE(t.tscore, 0) AS tscore,
         ((SELECT alpha FROM q) * COALESCE(v.vscore,0) + (1 - (SELECT alpha FROM q)) * COALESCE(tscore,0)) AS hybrid
  FROM vec v
  FULL OUTER JOIN trgm t ON t.segment_id = v.segment_id
)
SELECT s.id, s.document_id, s.text, s.start_offset, s.end_offset,
       s.page_no, s.paragraph_no, s.sentence_no,
       m.vscore, m.tscore, m.hybrid
FROM mix m
JOIN segments s ON s.id = m.segment_id
ORDER BY m.hybrid DESC
LIMIT :top_k
"""


