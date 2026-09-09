"""演示 task 工具：主 agent 派子助手，看两边的上下文各长成什么样。

跑法：  python3 demo_subagent.py      （用 MockModel，不花钱、不调 API）
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3_agent import Agent, build_agent, load_prompt
from v3_model import MockModel

# ---------- 台词：先是主 agent 的，中间穿插子助手的 ----------
SCRIPT = [
    # ① 主 agent：我不知道 div 在哪，派个助手去找
    ("我不认识这个项目，先派个子助手去定位除法函数在哪，省得我自己把整个目录读一遍。",
     ("task", {"prompt": "在当前目录的 Python 项目里找出哪个函数负责除法运算，"
                         "报告文件名、行号和函数原文。只看不要改。"})),

    # ②③④ 子助手：自己跑 ReAct（用的是同一个 MockModel，台词接着往下走）
    ("先看看有哪些文件。", ("bash", {"command": "ls"})),
    ("挨个看一下内容。", ("bash", {"command": "cat *.py"})),
    ("结论：除法在 utils.py 第 5 行的 safe_div(a, b)，原文是 `return a / b`，没有除零检查。",
     ("bash", {"command": "echo TASK_DONE"})),

    # ⑤ 主 agent：拿到结论，直接精确修改
    ("助手告诉我位置了，直接改。",
     ("edit_file", {"path": "utils.py",
                    "old": "    return a / b",
                    "new": '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b'})),
    ("改完了。", ("bash", {"command": "echo TASK_DONE"})),
    ("自检：任务是给除法加除零检查，已用 edit_file 加上，没做别的改动。结论：可以结束。",
     ("bash", {"command": "echo TASK_DONE"})),
]


def make_project():
    d = tempfile.mkdtemp(prefix="subagent_demo_")
    with open(os.path.join(d, "main.py"), "w") as f:
        f.write("from utils import safe_div\n\n" + "# 一堆无关代码 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n" * 300
                + "print(safe_div(10, 2))\n")
    with open(os.path.join(d, "utils.py"), "w") as f:
        f.write("# 工具函数\n" + "# 无关注释 yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\n" * 200
                + "\n\ndef safe_div(a, b):\n    return a / b\n")
    return d


def total_chars(messages):
    return sum(len(str(m.get("content") or "")) for m in messages)


cwd = make_project()
agent = build_agent(mock=True, cwd=cwd)
agent.model = MockModel(scripted=SCRIPT)
agent.run("给这个项目里的除法函数加上除零检查")

print("\n" + "=" * 70)
print("主 agent 的历史：")
for i, m in enumerate(agent.messages):
    c = str(m.get("content") or "").replace("\n", " ")
    print(f"  [{i:2}] {m['role']:9} {len(c):>6}  {c[:52]}{'…' if len(c) > 52 else ''}")

sub = agent.subagent_traces[0]
print(f"\n子助手的历史（{len(sub['messages'])} 条，主 agent 一条也没看见）：")
for i, m in enumerate(sub["messages"]):
    c = str(m.get("content") or "").replace("\n", " ")
    print(f"  [{i:2}] {m['role']:9} {len(c):>6}  {c[:52]}{'…' if len(c) > 52 else ''}")

print("\n" + "=" * 70)
print(f"主 agent 上下文    : {total_chars(agent.messages):>7,} 字符")
print(f"子助手内部烧掉    : {total_chars(sub['messages']):>7,} 字符  ← 用完即弃")
print(f"子助手回给主 agent: {len(agent.messages[3]['content']):>7,} 字符")


# ================== 对照组：不用 task，主 agent 自己翻 ==================
SCRIPT_FLAT = [
    ("先看看有哪些文件。", ("bash", {"command": "ls"})),
    ("挨个看一下内容。", ("bash", {"command": "cat *.py"})),
    ("找到了，在 utils.py 里。直接改。",
     ("edit_file", {"path": "utils.py",
                    "old": "    return a / b",
                    "new": '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b'})),
    ("改完了。", ("bash", {"command": "echo TASK_DONE"})),
    ("自检：任务是给除法加除零检查，已用 edit_file 加上。结论：可以结束。",
     ("bash", {"command": "echo TASK_DONE"})),
]

cwd2 = make_project()
flat = build_agent(mock=True, cwd=cwd2)
flat.verbose = False
flat.model = MockModel(scripted=SCRIPT_FLAT)
flat.run("给这个项目里的除法函数加上除零检查")


def billed(a):
    """每一步实际发出去的上下文加起来 = 真正计费的输入总量。"""
    return sum(x["chars"] for x in a.context_growth())


print("\n" + "=" * 70)
print(f"{'':16}{'步数':>5}{'最终上下文':>12}{'累计发出(计费)':>16}")
print("-" * 70)
print(f"{'用 task 派子助手':16}{agent.step_count:>5}{total_chars(agent.messages):>12,}{billed(agent):>16,}")
sub_billed = sum(x["chars"] for x in sub["info"]["context_growth"])
print(f"{'  └ 子助手那边':16}{sub['info']['steps']:>5}{total_chars(sub['messages']):>12,}{sub_billed:>16,}")
print(f"{'  └ 两边合计':16}{'':>5}{'':>12}{billed(agent) + sub_billed:>16,}")
print(f"{'不用，自己翻':16}{flat.step_count:>5}{total_chars(flat.messages):>12,}{billed(flat):>16,}")
print("-" * 70)

shutil.rmtree(cwd)
shutil.rmtree(cwd2)
