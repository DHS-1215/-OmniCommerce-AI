# -*- coding: utf-8 -*-
"""
创建时间    :2026/04/26 18:57
IDE       :PyCharm
作者      :董宏升
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
from fastapi import APIRouter

from app.api.v1.aftersales import router as aftersales_router
from app.api.v1.health import router as health_router
from app.api.v1.orders import router as orders_router
from app.api.v1.products import router as products_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.users import router as users_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.llm import router as llm_router
from app.api.v1.prompts import router as prompts_router
from app.api.v1.agents import router as agents_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)

api_v1_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"],
)
api_v1_router.include_router(
    products_router,
    prefix="/products",
    tags=["products"],
)
api_v1_router.include_router(
    orders_router,
    prefix="/orders",
    tags=["orders"],
)
api_v1_router.include_router(
    aftersales_router,
    prefix="/aftersales",
    tags=["aftersales"],
)
api_v1_router.include_router(
    tickets_router,
    prefix="/tickets",
    tags=["tickets"],
)

api_v1_router.include_router(
    prompts_router,
    prefix="/prompts",
    tags=["prompts"],
)

api_v1_router.include_router(
    llm_router,
    prefix="/llm",
    tags=["llm"],
)

api_v1_router.include_router(
    knowledge_router,
    prefix="/knowledge",
    tags=["knowledge"],
)

api_v1_router.include_router(
    agents_router,
    prefix="/agents",
    tags=["agents"],
)
