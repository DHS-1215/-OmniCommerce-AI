# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 16:16
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置对象。

    所有配置统一从环境变量或 .env.example 文件读取。
    禁止在业务代码中硬编码数据库地址、Redis 地址、密钥等配置。
    """

    model_config = SettingsConfigDict(
        env_file=".env.example",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="omni-commerce-ai", alias="APP_NAME")
    app_env: Literal["dev", "test", "prod"] = Field(default="dev", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")

    database_url: str = Field(
        default="postgresql+asyncpg://omni:omni_password@localhost:5432/omni_ai",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )

    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")

    jwt_secret_key: str = Field(default="change_me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Model Gateway
    default_llm_provider: str = Field(
        default="mock",
        alias="DEFAULT_LLM_PROVIDER",
    )
    default_embedding_provider: str = Field(
        default="mock",
        alias="DEFAULT_EMBEDDING_PROVIDER",
    )
    default_llm_model: str = Field(
        default="mock-chat-model",
        alias="DEFAULT_LLM_MODEL",
    )
    default_embedding_model: str = Field(
        default="mock-embedding-model",
        alias="DEFAULT_EMBEDDING_MODEL",
    )

    llm_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="LLM_BASE_URL",
    )
    llm_api_key: str = Field(
        default="",
        alias="LLM_API_KEY",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        alias="LLM_TIMEOUT_SECONDS",
    )
    llm_max_retries: int = Field(
        default=2,
        alias="LLM_MAX_RETRIES",
    )
    # RAG / Knowledge Base
    qdrant_url: str = Field(
        default="http://localhost:6333",
        alias="QDRANT_URL",
    )
    rag_vector_collection: str = Field(
        default="omni_knowledge_chunks",
        alias="RAG_VECTOR_COLLECTION",
    )
    rag_vector_size: int = Field(
        default=3,
        alias="RAG_VECTOR_SIZE",
    )
    rag_chunk_size: int = Field(
        default=500,
        alias="RAG_CHUNK_SIZE",
    )
    rag_chunk_overlap: int = Field(
        default=80,
        alias="RAG_CHUNK_OVERLAP",
    )
    rag_top_k: int = Field(
        default=5,
        alias="RAG_TOP_K",
    )
    rag_vector_weight: float = Field(
        default=0.65,
        alias="RAG_VECTOR_WEIGHT",
    )
    rag_keyword_weight: float = Field(
        default=0.35,
        alias="RAG_KEYWORD_WEIGHT",
    )
    rag_rerank_top_n: int = Field(
        default=5,
        alias="RAG_RERANK_TOP_N",
    )
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "omni_knowledge_chunks"
    opensearch_username: str | None = None
    opensearch_password: str | None = None

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "omni_minio"
    minio_secret_key: str = "omni_minio_password"
    minio_bucket_knowledge: str = "omni-knowledge"
    minio_secure: bool = False

    ocr_provider: str = "mock"


@lru_cache
def get_settings() -> Settings:
    """
    获取全局配置。

    使用 lru_cache 避免每次请求都重复读取环境变量或 .env.example 文件。
    """
    return Settings()
