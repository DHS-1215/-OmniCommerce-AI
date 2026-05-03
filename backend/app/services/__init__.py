# -*- coding: utf-8 -*-
"""
Service package.

业务服务层：
- 负责业务规则
- 负责组合 repository
- 负责事务提交 / 回滚
- 不直接构造 FastAPI Response
- 不调用模型
- 不实现 Agent / RAG
"""
