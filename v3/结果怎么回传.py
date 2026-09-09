"""命令跑完了，结果怎么告诉模型？

运行： python3 结果怎么回传.py
"""

import json

结果 = "<returncode>0</returncode>\n<output>\na.py\nb.py\n</output>"

print("场景：模型让我们跑 `ls`，我们跑完拿到了结果。")
print(f"     结果 = {结果!r}")
print("     现在要把它告诉模型。")


# ══════════════════════════════════════════════════════════════
print("\n" + "═" * 64)
print("  v2 的办法：假装是【用户】在说话")
print("═" * 64)

v2_messages = [
    {"role": "system", "content": "你是助手..."},
    {"role": "user", "content": "看看目录有什么"},
    {"role": "assistant", "content": "我先看看。\n\n```bash\nls\n```"},
    {"role": "user", "content": 结果},            # ← 结果塞在这
]

for i, m in enumerate(v2_messages):
    c = m["content"].replace("\n", "\\n")[:40]
    print(f"   [{i}] {m['role']:10s} {c}")

print("""
   ⚠ 问题：[3] 明明是机器跑出来的结果，却标成 role="user"
      在模型眼里，这是"用户发来的一条消息"。
      它得自己推断："哦，这其实是我上一条命令的执行结果"
""")


# ══════════════════════════════════════════════════════════════
print("═" * 64)
print("  v3 的办法：有专门的 role=\"tool\"")
print("═" * 64)

v3_messages = [
    {"role": "system", "content": "你是助手..."},
    {"role": "user", "content": "看看目录有什么"},
    {"role": "assistant", "content": "我先看看。",
     "tool_calls": [{"id": "call_001", "type": "function",
                     "function": {"name": "bash", "arguments": '{"command": "ls"}'}}]},
    {"role": "tool", "tool_call_id": "call_001", "content": 结果},   # ← 结果塞在这
]

for i, m in enumerate(v3_messages):
    c = (m.get("content") or "").replace("\n", "\\n")[:32]
    额外 = ""
    if "tool_calls" in m:
        额外 = f"   [发出 id={m['tool_calls'][0]['id']}]"
    if "tool_call_id" in m:
        额外 = f"   [回应 id={m['tool_call_id']}]"
    print(f"   [{i}] {m['role']:10s} {c}{额外}")

print("""
   ✅ [2] 发出一个调用，id = call_001
      [3] 用同一个 id 回应，role = "tool"
      配对关系写在协议里，模型不用猜
""")


# ══════════════════════════════════════════════════════════════
print("═" * 64)
print("  为什么 id 配对是必须的：一次发两个调用时")
print("═" * 64)

多个 = [
    {"role": "assistant", "content": "我同时看两样东西。",
     "tool_calls": [
         {"id": "call_A", "type": "function",
          "function": {"name": "bash", "arguments": '{"command": "ls"}'}},
         {"id": "call_B", "type": "function",
          "function": {"name": "bash", "arguments": '{"command": "pwd"}'}},
     ]},
    {"role": "tool", "tool_call_id": "call_B", "content": "/home/wayne"},     # 故意反着放
    {"role": "tool", "tool_call_id": "call_A", "content": "a.py\nb.py"},
]

print("\n   模型一次发了两个调用：")
for tc in 多个[0]["tool_calls"]:
    cmd = json.loads(tc["function"]["arguments"])["command"]
    print(f"      id={tc['id']}  命令={cmd!r}")

print("\n   我们回了两条结果（故意打乱顺序）：")
for m in 多个[1:]:
    print(f"      tool_call_id={m['tool_call_id']}  结果={m['content']!r}")

print("""
   ★ 就算顺序乱了，模型也能靠 id 对上号：
        call_A → ls   → 'a.py\\nb.py'
        call_B → pwd  → '/home/wayne'

   ★ 这就是你上次真跑时第 7 步发生的事 —— 一次两个调用，两条结果
""")


# ══════════════════════════════════════════════════════════════
print("═" * 64)
print("  代码上就是这一行的差别")
print("═" * 64)
print('''
   v2 (v2_agent.py):
       self.messages.append({"role": "user", "content": observation})

   v3 (v3_agent.py):
       self.messages.append({
           "role": "tool",                  # 换了角色
           "tool_call_id": tc["id"],        # 多带一个 id
           "content": observation,          # 内容一模一样
       })
''')
