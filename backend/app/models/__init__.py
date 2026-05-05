# -*- coding: utf-8 -*-
"""
SQLAlchemy 模型统一注册入口。

Alembic env.py 会导入 app.models，从而触发所有模型类注册到 Base.metadata。
"""
from app.models.auth import AuthAccount
from app.models.agent import AgentStepLog, AgentTask, ToolCallLog
from app.models.evaluation import EvaluationCase, EvaluationResult
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.llm import ModelCallLog
from app.models.order import OrderInfo, OrderItem
from app.models.product import Product, ProductReview, ProductSku
from app.models.prompt import PromptTemplate, PromptVersion
from app.models.ticket import AfterSaleTicket, CustomerServiceTicket
from app.models.user import UserProfile
from app.models.rag import RagRetrievalLog
from app.models.content_asset import ContentAsset
from app.models.content_review import ContentReview

__all__ = [
    "UserProfile",
    "Product",
    "ProductSku",
    "ProductReview",
    "OrderInfo",
    "OrderItem",
    "AfterSaleTicket",
    "CustomerServiceTicket",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "PromptTemplate",
    "PromptVersion",
    "ModelCallLog",
    "AgentTask",
    "AgentStepLog",
    "ToolCallLog",
    "EvaluationCase",
    "EvaluationResult",
    "RagRetrievalLog",
    "AuthAccount",
    "ContentAsset",
    "ContentReview",
]
