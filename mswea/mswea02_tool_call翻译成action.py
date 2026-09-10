"""mini-swe-agent 第二讲：Model 把 API tool_call 翻译成 action。

不联网，不导入官方依赖。
运行：python3 mswea/mswea02_tool_call翻译成action.py
"""

import json
from types import SimpleNamespace


def parse_toolcall_actions(tool_calls: list) -> list[dict]:
    """官方解析器的教学缩小版。"""
    actions = []
    for tool_call in tool_calls:
        args = json.loads(tool_call.function.arguments)
        actions.append(
            {
                "command": args["command"],
                "tool_call_id": tool_call.id,
            }
        )
    return actions


# 模拟 API 返回的一个 tool call。
# arguments 是 JSON 字符串，不是 Python 字典。
api_tool_call = SimpleNamespace(
    id="call_123",
    function=SimpleNamespace(
        name="bash",
        arguments='{"command": "ls -la"}',
    ),
)

print("【API 原始 tool_call】")
print("id       =", api_tool_call.id)
print("name     =", api_tool_call.function.name)
print("arguments=", repr(api_tool_call.function.arguments))
print("arguments 的类型 =", type(api_tool_call.function.arguments).__name__)

actions = parse_toolcall_actions([api_tool_call])

print("\n【Model 翻译后的 actions】")
print(actions)
print("command =", actions[0]["command"])

# Model.query() 最后把它放进 assistant message 的 extra 中。
message = {
    "role": "assistant",
    "content": "我先查看目录。",
    "extra": {"actions": actions},
}

print("\n【交给 Agent 的 message】")
print(json.dumps(message, ensure_ascii=False, indent=2))

assert message["extra"]["actions"][0] == {
    "command": "ls -la",
    "tool_call_id": "call_123",
}
print("\n✅ tool_call 已翻译成 Agent/Environment 认识的 action")
