# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/02 10:53
IDE       :PyCharm
作者      :董宏升

add rag retrieval log

Revision ID: 6b01_add_rag_retrieval_log
Revises: 9c9c22e1cf47
Create Date: 2026-05-02 00:00:00.000000
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6b01_add_rag_retrieval_log"
down_revision = "9c9c22e1cf47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_retrieval_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "retrieval_mode",
            sa.String(length=64),
            server_default="hybrid_opensearch",
            nullable=False,
        ),
        sa.Column("top_k", sa.Integer(), server_default="5", nullable=False),
        sa.Column("result_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "retrieved_chunk_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieved_document_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("vector_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("keyword_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("final_score", sa.Float(), server_default="0", nullable=False),
        sa.Column(
            "scores_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_rag_retrieval_log_tenant_id",
        "rag_retrieval_log",
        ["tenant_id"],
    )
    op.create_index(
        "ix_rag_retrieval_log_user_id",
        "rag_retrieval_log",
        ["user_id"],
    )
    op.create_index(
        "ix_rag_retrieval_log_request_id",
        "rag_retrieval_log",
        ["request_id"],
    )
    op.create_index(
        "ix_rag_retrieval_log_tenant_created_at",
        "rag_retrieval_log",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_rag_retrieval_log_request_created_at",
        "rag_retrieval_log",
        ["request_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_retrieval_log_request_created_at",
        table_name="rag_retrieval_log",
    )
    op.drop_index(
        "ix_rag_retrieval_log_tenant_created_at",
        table_name="rag_retrieval_log",
    )
    op.drop_index("ix_rag_retrieval_log_request_id", table_name="rag_retrieval_log")
    op.drop_index("ix_rag_retrieval_log_user_id", table_name="rag_retrieval_log")
    op.drop_index("ix_rag_retrieval_log_tenant_id", table_name="rag_retrieval_log")
    op.drop_table("rag_retrieval_log")
