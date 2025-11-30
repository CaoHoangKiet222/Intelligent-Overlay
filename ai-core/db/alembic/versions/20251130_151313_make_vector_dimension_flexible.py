"""make vector dimension flexible

Revision ID: 20251130_151313
Revises: 20251111_000001
Create Date: 2025-11-30 15:13:13.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20251130_151313"
down_revision: Union[str, None] = "20251111_000001_init_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat")
    
    op.execute("ALTER TABLE embeddings ADD COLUMN vector_new vector(16000)")
    
    op.execute("""
        DO $$
        DECLARE
            rec RECORD;
            vec_text text;
            vec_array float[];
            padding_array float[];
            expanded_vec text;
        BEGIN
            FOR rec IN SELECT id, vector::text as vec_str, dim FROM embeddings WHERE dim <= 16000
            LOOP
                BEGIN
                    vec_text := substring(rec.vec_str from 2 for length(rec.vec_str) - 2);
                    vec_array := string_to_array(vec_text, ',')::float[];
                    
                    IF array_length(vec_array, 1) < 16000 THEN
                        padding_array := ARRAY(SELECT 0.0::float FROM generate_series(1, 16000 - array_length(vec_array, 1)));
                        vec_array := vec_array || padding_array;
                    ELSIF array_length(vec_array, 1) > 16000 THEN
                        vec_array := vec_array[1:16000];
                    END IF;
                    
                    expanded_vec := '[' || array_to_string(vec_array, ',') || ']';
                    
                    EXECUTE format('UPDATE embeddings SET vector_new = %L::vector(16000) WHERE id = %L', expanded_vec, rec.id);
                EXCEPTION WHEN OTHERS THEN
                    CONTINUE;
                END;
            END LOOP;
        END $$;
    """)
    
    op.execute("ALTER TABLE embeddings DROP COLUMN vector")
    op.execute("ALTER TABLE embeddings RENAME COLUMN vector_new TO vector")
    op.execute("ALTER TABLE embeddings ALTER COLUMN vector SET NOT NULL")
    
    op.execute("""
        COMMENT ON COLUMN embeddings.vector IS 
        'Vector with max 16000 dimensions. Note: Indexes only support up to 2000 dimensions. '
        'For vectors > 2000 dim, queries will use sequential scan. Consider using dimension reduction for better performance.';
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat")
    op.execute("ALTER TABLE embeddings ALTER COLUMN vector TYPE vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivfflat "
        "ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
    )

