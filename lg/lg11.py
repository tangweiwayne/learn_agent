"""llm.invoke(messages) 这一趟：进去什么、出来什么、替代了你 v3 的哪几十行。

跑法：  python3 lg11.py     （不联网、不花钱）
"""
import json

from langchain_core.messages import (AIMessage, HumanMessage, SystemMessage,
                                     ToolMessage, convert_to_openai_messages)

print("=" * 74)
print("① 进去的是什么：一个消息列表")
print("=" * 74)
messages = [
    SystemMessage(content="你是一个能操作电脑的助手。"),
    HumanMessage(content="请完成这个任务：修好 main.py"),
    AIMessage(content="我先看看目录。",
              tool_calls=[{"name": "bash", "args": {"command": "ls"}, "id": "call_1"}]),
    ToolMessage(content="<returncode>0</returncode>\n<output>\nmain.py\n</output>",
                tool_call_id="call_1"),
]
print(f"  llm.invoke(messages)   ← messages 是 {len(messages)} 条：")
for i, m in enumerate(messages):
    print(f"     [{i}] {type(m).__name__}")

print()
print("=" * 74)
print("② LangChain 把这些对象转成 API 认识的字典（等于你的 for_api）")
print("=" * 74)
converted = convert_to_openai_messages(messages)
print("  " + json.dumps(converted, ensure_ascii=False, indent=2).replace("\n", "\n  "))

print()
print("=" * 74)
print("③ DeepSeek 返回的【原始 JSON】—— 你的 v3 拿到的就是这个")
print("=" * 74)
raw = {
    "id": "chatcmpl-abc",
    "choices": [{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "文件在这儿，我看一下内容。",
            "tool_calls": [{
                "id": "call_2",
                "type": "function",
                "function": {"name": "bash",
                             "arguments": "{\"command\": \"nl -ba main.py\"}"},
            }],
        },
        "finish_reason": "tool_calls",
    }],
    "usage": {"prompt_tokens": 523, "completion_tokens": 31, "total_tokens": 554},
}
print("  " + json.dumps(raw, ensure_ascii=False, indent=2).replace("\n", "\n  "))

print()
print("=" * 74)
print("④ LangChain 把它转成 AIMessage —— 对照表")
print("=" * 74)
ai = AIMessage(
    content=raw["choices"][0]["message"]["content"],
    tool_calls=[{
        "name": tc["function"]["name"],
        "args": json.loads(tc["function"]["arguments"]),
        "id": tc["id"],
    } for tc in raw["choices"][0]["message"]["tool_calls"]],
    response_metadata={"finish_reason": raw["choices"][0]["finish_reason"],
                       "token_usage": raw["usage"]},
    usage_metadata={"input_tokens": raw["usage"]["prompt_tokens"],
                    "output_tokens": raw["usage"]["completion_tokens"],
                    "total_tokens": raw["usage"]["total_tokens"]},
)
rows = [
    ("choices[0].message.content", "m.content", repr(ai.content)),
    ("choices[0].message.tool_calls[0].function.name", "m.tool_calls[0]['name']",
     repr(ai.tool_calls[0]["name"])),
    ("choices[0].message.tool_calls[0].function.arguments（字符串）",
     "m.tool_calls[0]['args']（已是字典）", repr(ai.tool_calls[0]["args"])),
    ("choices[0].message.tool_calls[0].id", "m.tool_calls[0]['id']",
     repr(ai.tool_calls[0]["id"])),
    ("choices[0].finish_reason", "m.response_metadata['finish_reason']",
     repr(ai.response_metadata["finish_reason"])),
    ("usage.prompt_tokens", "m.usage_metadata['input_tokens']",
     repr(ai.usage_metadata["input_tokens"])),
    ("usage.completion_tokens", "m.usage_metadata['output_tokens']",
     repr(ai.usage_metadata["output_tokens"])),
]
for a, b, c in rows:
    print(f"  {a}")
    print(f"      → {b}  =  {c}")

print()
print("=" * 74)
print("⑤ 算钱：usage 就在 AIMessage 里")
print("=" * 74)
PRICE_IN, PRICE_OUT = 0.27 / 1e6, 1.10 / 1e6
u = ai.usage_metadata
cost = u["input_tokens"] * PRICE_IN + u["output_tokens"] * PRICE_OUT
print(f"  ai.usage_metadata = {u}")
print(f"  花费 = {u['input_tokens']} × {PRICE_IN} + {u['output_tokens']} × {PRICE_OUT}"
      f" = ${cost:.6f}")
