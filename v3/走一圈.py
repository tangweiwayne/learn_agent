"""跟着一条命令 ls 走一圈，看 v2 和 v3 每一步的实际数据。

用法： python3 走一圈.py
改改下面的数据再跑，感受一下。
"""

import json
import re


def 分隔(t):
    print("\n" + "━" * 70)
    print("  " + t)
    print("━" * 70)


def 打印json(标签, obj):
    print(f"\n  {标签}")
    for line in json.dumps(obj, ensure_ascii=False, indent=2).splitlines():
        print("     " + line)


# ══════════════════════════════════════════════════════════════
分隔("① 我们发给 API 的东西")

v2_请求 = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是助手。每次回复必须恰好一个 ```bash 代码块...（15行格式说明）"},
        {"role": "user", "content": "统计 .py 文件数量"},
    ],
}

v3_请求 = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是助手。你有一个工具：bash。"},
        {"role": "user", "content": "统计 .py 文件数量"},
    ],
    "tools": [{                                  # ← v3 唯一新增的字段
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行一条 bash 命令",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    }],
}

打印json("v2 请求:", v2_请求)
打印json("v3 请求:", v3_请求)


# ══════════════════════════════════════════════════════════════
分隔("② API 返回什么")

v2_返回消息 = {
    "role": "assistant",
    "content": "先看目录：\n\n```bash\nls\n```\n\n再数一下：\n\n```bash\nls *.py | wc -l\n```",
}

v3_返回消息 = {
    "role": "assistant",
    "content": "我先看看当前目录里有什么文件。",        # 只有思考
    "tool_calls": [{                                # 命令单独一个字段
        "id": "call_9x7k2",
        "type": "function",
        "function": {"name": "bash", "arguments": '{"command": "ls"}'},
    }],
}

打印json("v2 返回的 message:", v2_返回消息)
打印json("v3 返回的 message:", v3_返回消息)


# ══════════════════════════════════════════════════════════════
分隔("③ 怎么把命令取出来")

print("\n  ▼ v2：正则去挖")
content = v2_返回消息["content"]
blocks = re.findall(r"```bash\n(.*?)\n```", content, re.DOTALL)
print(f"     content = {content!r}")
print(f"     blocks  = re.findall(...)  →  {blocks}")
print(f"     检查     if len(blocks) != 1: raise ValueError")
print(f"     命令     = {blocks[0].strip()!r}")

print("\n  ▼ v3：直接读字段")
tc = v3_返回消息["tool_calls"][0]
print(f"     tc                          = {json.dumps(tc, ensure_ascii=False)}")
print(f"     tc['function']['arguments'] = {tc['function']['arguments']!r}   ← 字符串！")
args = json.loads(tc["function"]["arguments"])
print(f"     json.loads(...)             = {args}")
print(f"     命令                        = {args['command']!r}")
print("     ★ 没有 if，没有 raise —— 格式由 API 保证")


# ══════════════════════════════════════════════════════════════
分隔("④ 执行结果怎么塞回对话")

输出 = "<returncode>0</returncode>\n<output>\na.py\nb.py\n</output>"

打印json("v2（伪装成用户说话）:", {"role": "user", "content": 输出})
打印json("v3（正经的 tool 角色）:",
         {"role": "tool", "tool_call_id": tc["id"], "content": 输出})
print(f"\n     ★ tool_call_id={tc['id']!r} 和第②步那个 id 相同 —— 一问一答配对")


# ══════════════════════════════════════════════════════════════
分隔("⑤ 第二轮的 messages 角色序列")

v2_messages = v2_请求["messages"] + [v2_返回消息, {"role": "user", "content": 输出}]
v3_messages = v3_请求["messages"] + [v3_返回消息,
                                     {"role": "tool", "tool_call_id": tc["id"], "content": 输出}]

for 名, msgs in [("v2", v2_messages), ("v3", v3_messages)]:
    print(f"\n  ▼ {名}")
    for i, m in enumerate(msgs):
        额外 = ""
        if "tool_calls" in m:
            额外 = f"   🔧 tool_calls[id={m['tool_calls'][0]['id']}]"
        if "tool_call_id" in m:
            额外 = f"   ↩ 回应 {m['tool_call_id']}"
        print(f"     [{i}] {m['role']:10s}{额外}")

print("""
  ★ v2 只有 system/user/assistant 三种角色，命令和结果都混在文字里
  ★ v3 多了 tool 角色，命令和结果都是结构化字段
""")
