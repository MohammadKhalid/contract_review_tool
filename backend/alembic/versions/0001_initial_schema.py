"""Initial schema: contracts + legal knowledge base with pgvector

Revision ID: 0001
Revises: 
Create Date: 2026-05-29

This is the baseline migration that creates the complete current schema.
It was written by hand after autogenerate missed several tables (a known
occasional issue with pgvector + Alembic on first run). The models in
models/contract.py and models/legal_kb.py are the source of truth.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# pgvector is required for the Vector column type in both upgrade and downgrade paths
import pgvector.sqlalchemy  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (required before any Vector columns)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # --- legal_sources -------------------------------------------------
    op.create_table(
        "legal_sources",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("jurisdiction", sa.String(), nullable=True),
        sa.Column("publisher", sa.String(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("retrieved_at", sa.String(), nullable=True),
        sa.Column("license_note", sa.String(), nullable=True),
    )

    # --- legal_documents ------------------------------------------------
    op.create_table(
        "legal_documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("legal_sources.id"),
            nullable=False,
        ),
        sa.Column("citation", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "keywords",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # --- contracts ------------------------------------------------------
    op.create_table(
        "contracts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("upload_date", sa.DateTime(), nullable=True),
        sa.Column("processing_method", sa.String(), nullable=True),
    )

    # --- contract_analyses ---------------------------------------------
    op.create_table(
        "contract_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "contract_id",
            sa.Integer(),
            sa.ForeignKey("contracts.id"),
            nullable=False,
        ),
        sa.Column("analysis_date", sa.DateTime(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("sentence_count", sa.Integer(), nullable=True),
        sa.Column(
            "key_terms",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "named_entities",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "potential_issues",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("processing_time_seconds", sa.Integer(), nullable=True),
        sa.Column("ocr_used", sa.String(), nullable=True),
    )

    # --- legal_chunks (with pgvector) ----------------------------------
    op.create_table(
        "legal_chunks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("legal_documents.id"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(dim=384),
            nullable=False,
        ),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # ivfflat index for vector similarity search on legal_chunks
    op.create_index(
        "legal_chunks_embedding_idx",
        "legal_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="ivfflat",
    )

    # --- invalid_clause_patterns (with pgvector) -----------------------
    op.create_table(
        "invalid_clause_patterns",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("clause_pattern", sa.Text(), nullable=False),
        sa.Column("why_invalid", sa.Text(), nullable=False),
        sa.Column("legal_basis", sa.String(), nullable=True),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("example_text", sa.Text(), nullable=True),
        sa.Column("recommended_response", sa.Text(), nullable=True),
        sa.Column(
            "source_document_id",
            sa.Integer(),
            sa.ForeignKey("legal_documents.id"),
            nullable=True,
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(dim=384),
            nullable=True,
        ),
        sa.Column("bgb_citation", sa.String(), nullable=True),
        sa.Column("bgb_text_excerpt", sa.Text(), nullable=True),
    )

    # ivfflat index for vector similarity search on invalid clause patterns
    op.create_index(
        "invalid_clause_embedding_idx",
        "invalid_clause_patterns",
        ["embedding"],
        unique=False,
        postgresql_using="ivfflat",
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index(
        "invalid_clause_embedding_idx",
        table_name="invalid_clause_patterns",
        postgresql_using="ivfflat",
    )
    op.drop_table("invalid_clause_patterns")

    op.drop_index(
        "legal_chunks_embedding_idx",
        table_name="legal_chunks",
        postgresql_using="ivfflat",
    )
    op.drop_table("legal_chunks")

    op.drop_table("contract_analyses")
    op.drop_table("contracts")
    op.drop_table("legal_documents")
    op.drop_table("legal_sources")

    # Note: We intentionally do NOT drop the vector extension on downgrade.
    # Other databases or future migrations may still need it.
