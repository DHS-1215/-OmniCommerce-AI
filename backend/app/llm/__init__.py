# -*- coding: utf-8 -*-
"""
模型网关模块。

所有 LLM / Embedding / Rerank 相关调用必须统一经过本模块。
禁止 Agent / RAG / 业务 service 直接调用模型 Provider API。
"""