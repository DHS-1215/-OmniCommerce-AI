# -*- coding: utf-8 -*-
from __future__ import annotations

"""
创建时间    :2026/05/01 09:09
IDE       :PyCharm
作者      :董宏升

Prompt 变量渲染器。

本文件只负责：
- 从 Prompt 内容中识别 {{ variable_name }} 变量；
- 校验必填变量；
- 将变量替换为传入值；
- 返回渲染后的 Prompt 文本。

注意：
- 不读取数据库；
- 不调用模型网关；
- 不写 Prompt 版本管理逻辑；
- 不实现 Agent / RAG。
"""
# 每次解决问题，我都在成长，不要着急，不要气馁！
import re
from typing import Any

from starlette import status

from app.core.exceptions import BaseAppException

_VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


class PromptRenderer:
    """
    Prompt 变量渲染器。

    变量格式统一使用：

        {{variable_name}}

    或：

        {{ variable_name }}

    不支持执行表达式，不支持函数调用，不支持任意 Python 代码。
    这是为了避免 Prompt 模板变成脚本执行器。
    """

    def extract_variables(self, content: str) -> set[str]:
        """
        从 Prompt 内容中提取变量名。

        示例：
            "你好，{{user_name}}，订单 {{ order_no }}"
            -> {"user_name", "order_no"}
        """

        return set(_VARIABLE_PATTERN.findall(content or ""))

    def render(
            self,
            *,
            content: str,
            variables: dict[str, Any] | None = None,
            variable_schema_json: dict[str, Any] | None = None,
    ) -> str:
        """
        渲染 Prompt 内容。

        参数：
            content:
                Prompt 原始模板内容。

            variables:
                本次渲染传入的变量。

            variable_schema_json:
                变量 Schema。
                当前支持两种轻量格式：

                方式一：
                {
                    "required": ["user_question", "order_no"]
                }

                方式二：
                {
                    "properties": {
                        "user_question": {"type": "string", "required": true},
                        "order_no": {"type": "string", "required": true}
                    }
                }

        返回：
            渲染后的 Prompt 文本。
        """

        variables = variables or {}
        variable_schema_json = variable_schema_json or {}

        template_variables = self.extract_variables(content)
        required_variables = self._get_required_variables(variable_schema_json)

        missing_required_variables = sorted(
            name for name in required_variables if name not in variables
        )
        if missing_required_variables:
            raise BaseAppException(
                code="PROMPT_RENDER_VARIABLE_MISSING",
                message="Prompt 渲染缺少必填变量",
                status_code=status.HTTP_400_BAD_REQUEST,
                data={"missing_variables": missing_required_variables},
            )

        missing_template_variables = sorted(
            name for name in template_variables if name not in variables
        )
        if missing_template_variables:
            raise BaseAppException(
                code="PROMPT_RENDER_VARIABLE_MISSING",
                message="Prompt 模板变量未提供",
                status_code=status.HTTP_400_BAD_REQUEST,
                data={"missing_variables": missing_template_variables},
            )

        self._validate_variable_types(
            variables=variables,
            variable_schema_json=variable_schema_json,
        )

        def replace(match: re.Match[str]) -> str:
            variable_name = match.group(1)
            value = variables.get(variable_name)

            if value is None:
                return ""

            if isinstance(value, str):
                return value

            if isinstance(value, bool):
                return "true" if value else "false"

            return str(value)

        return _VARIABLE_PATTERN.sub(replace, content)

    def _get_required_variables(
            self,
            variable_schema_json: dict[str, Any],
    ) -> set[str]:
        """
        从 variable_schema_json 中提取必填变量。
        """

        required_variables: set[str] = set()

        raw_required = variable_schema_json.get("required")
        if isinstance(raw_required, list):
            required_variables.update(
                item for item in raw_required if isinstance(item, str)
            )

        properties = variable_schema_json.get("properties")
        if isinstance(properties, dict):
            for name, config in properties.items():
                if not isinstance(name, str):
                    continue

                if isinstance(config, dict) and config.get("required") is True:
                    required_variables.add(name)

        return required_variables

    def _validate_variable_types(
            self,
            *,
            variables: dict[str, Any],
            variable_schema_json: dict[str, Any],
    ) -> None:
        """
        轻量变量类型校验。

        当前只做常见类型校验：
        - string
        - integer
        - number
        - boolean
        - array
        - object

        这里不引入 jsonschema 依赖，避免窗口 5 为简单变量校验新增依赖。
        后续如果总控确认需要完整 JSON Schema 校验，再统一引入。
        """

        properties = variable_schema_json.get("properties")
        if not isinstance(properties, dict):
            return

        errors: list[dict[str, Any]] = []

        for name, config in properties.items():
            if not isinstance(name, str) or not isinstance(config, dict):
                continue

            if name not in variables:
                continue

            expected_type = config.get("type")
            if not isinstance(expected_type, str):
                continue

            value = variables[name]
            if not self._matches_type(value=value, expected_type=expected_type):
                errors.append(
                    {
                        "variable": name,
                        "expected_type": expected_type,
                        "actual_type": type(value).__name__,
                    }
                )

        if errors:
            raise BaseAppException(
                code="PROMPT_RENDER_VARIABLE_INVALID",
                message="Prompt 渲染变量类型不符合声明",
                status_code=status.HTTP_400_BAD_REQUEST,
                data={"errors": errors},
            )

    def _matches_type(self, *, value: Any, expected_type: str) -> bool:
        """
        判断变量值是否符合声明类型。
        """

        if expected_type == "string":
            return isinstance(value, str)

        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)

        if expected_type == "number":
            return isinstance(value, int | float) and not isinstance(value, bool)

        if expected_type == "boolean":
            return isinstance(value, bool)

        if expected_type == "array":
            return isinstance(value, list)

        if expected_type == "object":
            return isinstance(value, dict)

        # 未识别类型不强行拦截，避免过早扩大规则范围。
        return True
