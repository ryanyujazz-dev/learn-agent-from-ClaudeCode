# Lesson 5 — 工具系统设计

## 行业术语：Tool Calling

本课涉及的概念在行业里有标准叫法：

| 术语 | 含义 | 本课对应 |
|------|------|---------|
| **Tool Schema** | 用 JSON Schema 定义工具接受什么参数（告诉 LLM 怎么用） | `input_schema` |
| **Tool Calling / Function Calling** | LLM 决定调用哪个函数、传什么参数 | 第 6 课讲 |
| **Tool Dispatch** | 程序根据 LLM 返回的工具名，路由到对应的处理函数 | 第 6 课讲 |
| **Tool Result** | 工具执行完的结果，回喂给 LLM | `ToolResult` |

本课重点讲 **Tool Schema**（定义工具长什么样）和 **ToolResult**（工具返回什么）。第 6 课讲 Tool Calling 和 Tool Dispatch。

## 本节新概念

**ABC 抽象基类**：定义一个"模板"，强制所有工具都实现相同的接口。

## 为什么需要抽象？

如果没有统一接口，每个工具长得不一样，agentic loop 就不知道怎么调用它们。
有了抽象基类，所有工具都保证有 `name`、`call()` 方法，loop 可以统一处理。

## 核心代码解读

```python
from abc import ABC, abstractmethod

class Tool(ABC):
    name: str = ""

    @abstractmethod
    async def call(self, args: dict) -> str:
        ...  # 子类必须实现这个方法
```

`@abstractmethod` 的意思是：如果你继承了 `Tool` 但没有实现 `call()`，Python 会报错。

```python
from dataclasses import dataclass

@dataclass
class ToolResult:
    data: str
    error: bool = False
```

`@dataclass` 自动生成 `__init__`，省去手写构造函数。

## JSON Schema

LLM 需要知道每个工具接受什么参数，我们用 JSON Schema 描述：

```python
input_schema = {
    "type": "object",
    "properties": {
        "message": {"type": "string", "description": "要回显的内容"}
    },
    "required": ["message"]
}
```

## 运行

```bash
python3 tool_design.py
```

## 作业

实现一个 `AddTool`：接受 `a` 和 `b` 两个数字，返回它们的和。
