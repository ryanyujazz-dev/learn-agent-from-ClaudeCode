"""
Lesson 5: 工具系统设计
新概念: ABC 抽象基类, @abstractmethod, dataclass, JSON Schema
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    data: str
    error: bool = False


class Tool(ABC):
    name: str = ""
    description_text: str = ""
    input_schema: dict = {}

    @abstractmethod
    async def call(self, args: dict) -> ToolResult:
        ...

    def to_api_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description_text,
                "parameters": self.input_schema,
            },
        }


class EchoTool(Tool):
    name = "echo"
    description_text = "原样返回输入的消息"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "要回显的内容"},
        },
        "required": ["message"],
    }

    async def call(self, args: dict) -> ToolResult:
        return ToolResult(data=args["message"])


# 演示
import json

tool = EchoTool()
print(f"工具名称: {tool.name}")
print(f"API Schema:\n{json.dumps(tool.to_api_schema(), ensure_ascii=False, indent=2)}")
