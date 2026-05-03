from __future__ import annotations

import os


"""
测试环境代理隔离。

Windows / Conda / 本地代理工具可能会设置 HTTP_PROXY / HTTPS_PROXY / ALL_PROXY，
httpx 默认会读取这些环境变量，导致访问 localhost / 127.0.0.1 时误走代理，
出现 502 Bad Gateway。

本项目的 API 集成测试全部访问本地 Docker 服务，因此测试进程内默认禁用代理。
"""

_LOCAL_NO_PROXY = "127.0.0.1,localhost"

os.environ["NO_PROXY"] = _LOCAL_NO_PROXY
os.environ["no_proxy"] = _LOCAL_NO_PROXY

for proxy_env_name in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(proxy_env_name, None)