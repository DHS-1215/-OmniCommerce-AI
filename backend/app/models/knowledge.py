# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/04/26 20:55
IDE       :PyCharm
作者      :董宏升

企业知识库文档与切片模型。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import uuid

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import BusinessBaseMixin


class KnowledgeDocument(BusinessBaseMixin, Base):
    """
    知识库文档表。

    表名：knowledge_document

    用途：
    - 保存企业知识库文档元数据
    - 后续 RAG 文档上传、解析、切片从该表开始
    """

    __tablename__ = "knowledge_document"

    document_no: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="文档业务编号",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="文档标题",
    )

    source_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="upload",
        index=True,
        comment="来源类型：upload/url/manual/api",
    )

    source_uri: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="来源 URI",
    )

    storage_object_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="对象存储 Key",
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="MIME 类型",
    )

    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="文件大小，单位 byte",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="uploaded",
        index=True,
        comment="文档状态：uploaded/parsing/chunked/indexed/failed/disabled",
    )

    parser_status: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="解析状态：pending/running/success/failed",
    )

    language: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="语言，例如 zh-CN/en-US",
    )

    acl_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="访问控制元数据 JSON，供后续 RAG ACL 过滤使用",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    chunks = relationship(
        "KnowledgeChunk",
        back_populates="document",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_no",
            name="uq_knowledge_document_tenant_document_no",
        ),
        Index(
            "ix_knowledge_document_tenant_status",
            "tenant_id",
            "status",
        ),
        Index(
            "ix_knowledge_document_tenant_source_type",
            "tenant_id",
            "source_type",
        ),
    )


class KnowledgeChunk(BusinessBaseMixin, Base):
    """
    知识库切片表。

    表名：knowledge_chunk

    用途：
    - 保存文档切片文本、关键词、向量索引关联信息
    - 后续 RAG 混合检索和引用溯源依赖该表
    """

    __tablename__ = "knowledge_chunk"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_document.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="文档 ID",
    )

    chunk_no: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="切片业务编号",
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="文档标题冗余，便于检索返回",
    )

    source_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="来源类型冗余",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="切片正文",
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="切片内容哈希",
    )

    page_no: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="页码",
    )

    section_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="章节标题",
    )

    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="切片 token 数预估",
    )

    keywords_json: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="关键词 JSON",
    )

    embedding_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="向量库 embedding/vector ID",
    )

    vector_collection: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="向量集合名称",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="扩展元数据 JSON",
    )

    document = relationship(
        "KnowledgeDocument",
        back_populates="chunks",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_no",
            name="uq_knowledge_chunk_tenant_document_chunk_no",
        ),
        Index(
            "ix_knowledge_chunk_tenant_document",
            "tenant_id",
            "document_id",
        ),
        Index(
            "ix_knowledge_chunk_tenant_embedding",
            "tenant_id",
            "embedding_id",
        ),
    )
