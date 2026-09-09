"""测打断：在最危险的位置（模型回完话、工具还没跑）抛 KeyboardInterrupt，
看历史有没有被补完整、插话有没有进去。

跑法：  python3 test_interrupt.py     （不联网、不花钱）
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_agent import build_agent
from v3_model import MockModel

SCRIPT = [
    ("我先看看目录。", ("bash", {"command": "ls"})),
    ("现在改文件。", ("edit_file", {"path": "a.py", "old": "x = 1", "new": "x = 2"})),
    ("好了。", ("bash", {"command": "echo TASK_DONE"})),
    ("自检通过。", ("bash", {"command": "echo TASK_DONE"})),
]


def build(answers):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "a.py"), "w").write("x = 1\n")
    a = build_agent(mock=True, cwd=d)
    a.model = MockModel(scripted=SCRIPT)
    a.verbose = False
    it = iter(answers)
    a.ask_human = lambda prompt: next(it)
    return a


def dump(agent, title):
    print(f"\n--- {title} ---")
    for i, m in enumerate(agent.messages):
        c = str(m.get("content") or "").replace("\n", " ")
        tag = ""
        for tc in m.get("tool_calls") or []:
            tag += f" 🔧{tc['function']['name']}(id={tc['id']})"
        tid = f" ↩{m['tool_call_id']}" if m.get("tool_call_id") else ""
        print(f"  [{i:2}] {m['role']:9}{tid}{tag}  {c[:56]}")


def dangling(agent):
    """还有几个没人回应的 tool_call —— 这个数必须是 0，否则下次请求会 400。"""
    answered = {m.get("tool_call_id") for m in agent.messages if m["role"] == "tool"}
    return sum(1 for m in agent.messages for tc in (m.get("tool_calls") or [])
               if tc["id"] not in answered)


# ============ 场景 1：打断在最危险的位置，然后插话 ============
print("=" * 70)
print("场景1：第 2 步模型已回话、edit_file 还没执行时按 Ctrl-C，插一句话")
agent = build(["先别改文件，改成只打印文件内容"])

真 = agent.call_tool
def 假(name, args):
    if name == "edit_file":
        raise KeyboardInterrupt        # ← 就在这里打断
    return 真(name, args)
agent.call_tool = 假

agent.run("把 a.py 里的 x 改成 2")
dump(agent, "打断并插话之后的 messages")
print(f"\n  悬空的 tool_call 数 = {dangling(agent)}  （必须是 0）")
print(f"  被打断次数 = {agent.interrupts}")

ok1 = dangling(agent) == 0 and any(
    "用户中途插话" in str(m.get("content") or "") for m in agent.messages)

# ============ 场景 2：打断后选 q，直接结束 ============
print("\n" + "=" * 70)
print("场景2：同样位置打断，输入 q 结束")
agent2 = build(["q"])
真2 = agent2.call_tool
def 假2(name, args):
    if name == "edit_file":
        raise KeyboardInterrupt
    return 真2(name, args)
agent2.call_tool = 假2
agent2.run("把 a.py 里的 x 改成 2")
print(f"  跑完后消息 {len(agent2.messages)} 条，悬空 tool_call = {dangling(agent2)}")
print(f"  最后一条: {agent2.messages[-1]['role']} — "
      f"{str(agent2.messages[-1].get('content'))[:60]}")
ok2 = dangling(agent2) == 0 and len(agent2.messages) < len(agent.messages)

# ============ 场景 3：回车继续 ============
print("\n" + "=" * 70)
print("场景3：同样位置打断，直接回车继续")
agent3 = build([""])
真3 = agent3.call_tool
第一次 = [True]
def 假3(name, args):
    if name == "edit_file" and 第一次[0]:
        第一次[0] = False
        raise KeyboardInterrupt
    return 真3(name, args)
agent3.call_tool = 假3
agent3.run("把 a.py 里的 x 改成 2")
print(f"  跑完后消息 {len(agent3.messages)} 条，悬空 tool_call = {dangling(agent3)}")
print(f"  插话消息数 = "
      f"{sum(1 for m in agent3.messages if '用户中途插话' in str(m.get('content') or ''))}（应为 0）")
ok3 = dangling(agent3) == 0

print("\n" + "=" * 70)
print("✅ 全部通过" if (ok1 and ok2 and ok3) else "❌ 有失败")
