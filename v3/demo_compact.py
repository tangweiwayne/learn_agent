"""演示 Agent.compact()：一步一步长历史，看每一步【存着的】和【发出去的】差多少。

跑法：  python3 demo_compact.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_agent import Agent
from v3_model import for_api

KEEP_STEPS = 3
MIN_CHARS = 800


class StubAgent:
    """只借 compact() 这一个方法，不用真的建 Agent（要 model/env/prompt，太重）。"""
    compact_keep_steps = KEEP_STEPS
    compact_min_chars = MIN_CHARS


compact = Agent.compact.__get__(StubAgent())


def total_chars(messages):
    return sum(len(str(m.get("content") or "")) for m in messages)


def make_call(step):
    return [{"id": f"call_{step}", "type": "function",
             "function": {"name": "bash", "arguments": '{"command":"cat main.py"}'}}]


# ---- 开场 ----
messages = [
    {"role": "system", "content": "你是一个命令行 agent。" * 5},
    {"role": "user", "content": "修好 main.py 里的 bug。"},
]

print(f"配置: compact_keep_steps={KEEP_STEPS}  compact_min_chars={MIN_CHARS}\n")
print(f"{'步':>3} {'存着(chars)':>12} {'发出去(chars)':>14} {'省':>10}  {'压掉的下标':<14} 说明")
print("-" * 78)

OUTPUTS = [3000, 200, 5000, 150, 900, 120]        # 每步命令输出的长度
NOTE = ["cat 大文件", "短输出", "cat 另一个大文件", "短输出", "中等输出", "短输出"]

for step, (n, note) in enumerate(zip(OUTPUTS, NOTE), start=1):
    messages.append({"role": "assistant", "content": f"第 {step} 步：我看一下",
                     "tool_calls": make_call(step)})
    messages.append({"role": "tool", "tool_call_id": f"call_{step}",
                     "name": "bash", "content": f"[第{step}步输出]" + "X" * n})

    sent = compact(messages)
    squeezed = [i for i, (a, b) in enumerate(zip(messages, sent))
                if len(str(a.get("content") or "")) != len(b["content"])]
    before, after = total_chars(messages), total_chars(sent)
    print(f"{step:>3} {before:>12,} {after:>14,} {before - after:>10,}  "
          f"{str(squeezed):<14} {note}")

print("-" * 78)
print(f"\n最后一步发出去的历史（{len(sent)} 条，一条没少）：")
for i, m in enumerate(for_api(sent)):
    c = m["content"]
    preview = c[:46].replace("\n", " ")
    tail = "…" if len(c) > 46 else ""
    print(f"  [{i:2}] {m['role']:9} {len(c):>6}  {preview}{tail}")

print(f"\n★ self.messages 仍是完整的：{total_chars(messages):,} 字符，trace 里存的是这份。")
