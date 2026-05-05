# -*- coding: utf-8 -*-
"""
创建时间    :2026/05/05 08:32
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
"""create auth account

Revision ID: e13_create_auth_account
Revises: d62c219e9482
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e13_create_auth_account"
down_revision: Union[str, Sequence[str], None] = "d62c219e9482"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_account",
        sa.Column("user_id", sa.UUID(), nullable=False, comment="关联 user_profile.id"),
        sa.Column("username", sa.String(length=128), nullable=False, comment="登录用户名"),
        sa.Column("password_hash", sa.String(length=512), nullable=False, comment="密码 hash，不存储明文密码"),
        sa.Column("role", sa.String(length=32), nullable=False, comment="角色：admin/operator/viewer"),
        sa.Column("status", sa.String(length=32), nullable=False, comment="账号状态：active/disabled"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True, comment="最后登录时间"),
        sa.Column("id", sa.UUID(), nullable=False, comment="主键 ID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="租户 ID"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.CheckConstraint("role in ('admin', 'operator', 'viewer')", name="ck_auth_account_role"),
        sa.CheckConstraint("status in ('active', 'disabled')", name="ck_auth_account_status"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profile.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "username", name="uq_auth_account_tenant_username"),
    )
    op.create_index(op.f("ix_auth_account_deleted_at"), "auth_account", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_auth_account_tenant_id"), "auth_account", ["tenant_id"], unique=False)
    op.create_index("ix_auth_account_tenant_role", "auth_account", ["tenant_id", "role"], unique=False)
    op.create_index("ix_auth_account_tenant_status", "auth_account", ["tenant_id", "status"], unique=False)
    op.create_index("ix_auth_account_tenant_user", "auth_account", ["tenant_id", "user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_account_tenant_user", table_name="auth_account")
    op.drop_index("ix_auth_account_tenant_status", table_name="auth_account")
    op.drop_index("ix_auth_account_tenant_role", table_name="auth_account")
    op.drop_index(op.f("ix_auth_account_tenant_id"), table_name="auth_account")
    op.drop_index(op.f("ix_auth_account_deleted_at"), table_name="auth_account")
    op.drop_table("auth_account")
