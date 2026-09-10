"""LangGraph 最小例子：不用模型、不联网、不花钱。

一个数字从 0 开始，每次加 3，超过 10 就停。
用它认清三个词：State（笔记本）、Node（工位）、Edge（箭头）。

跑法：  python3 lg01.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# ========== ① State：传送带上那本笔记本 ==========
class CounterState(TypedDict):
    number: int
    history: list


# ========== ② Node：工位。拿到笔记本，返回"要改哪几页" ==========
def add_three(state: CounterState) -> dict:
    new_value = state["number"] + 3
    print(f"   [工位 add_three] {state['number']} + 3 = {new_value}")
    return {"number": new_value, "history": state["history"] + [new_value]}


# ========== ③ Edge：岔路口。返回下一站的名字 ==========
def should_continue(state: CounterState) -> str:
    if state["number"] > 10:
        print(f"   [岔路口] {state['number']} > 10 → 收工")
        return "done"
    print(f"   [岔路口] {state['number']} 还不到 10 → 回去再加")
    return "loop"


# ========== 画图 ==========
builder = StateGraph(CounterState)
builder.add_node("add_three", add_three)          # 放一个工位
builder.add_edge(START, "add_three")              # 开始 → add_three
builder.add_conditional_edges(                    # add_three 之后走哪条路，问 should_continue
    "add_three", should_continue,
    {"loop": "add_three", "done": END},           # 它返回 loop 就回自己，返回 done 就结束
)
app = builder.compile()

# ========== 跑 ==========
print("笔记本初始内容 = {'number': 0, 'history': []}\n")
result = app.invoke({"number": 0, "history": []})
print(f"\n笔记本最终内容 = {result}")

print("\n===== 这张图长什么样 =====")
print(app.get_graph().draw_mermaid())
