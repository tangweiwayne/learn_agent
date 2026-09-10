"""三个问题的答案：state 是什么 / Annotated 是什么 / add_messages 干了什么。

跑法：  python3 lg06.py     （不联网、不花钱）
"""
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

print("=" * 70)
print("问题1：state 到底是什么？—— 就是一个普通字典")
print("=" * 70)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def peek(state):
    print(f"  type(state)       = {type(state)}")
    print(f"  state 本身         = {state}")
    print(f"  state.keys()      = {list(state.keys())}")
    print(f"  state['messages'] 是 {type(state['messages']).__name__}，"
          f"长度 {len(state['messages'])}")
    return {"messages": [AIMessage(content="收到")]}


builder = StateGraph(AgentState)
builder.add_node("peek", peek)
builder.add_edge(START, "peek")
builder.add_edge("peek", END)
builder.compile().invoke({"messages": [HumanMessage(content="你好")]})

print()
print("=" * 70)
print("问题2：add_messages 是个【普通函数】，可以自己单独调")
print("=" * 70)
old = [SystemMessage(content="你是助手"), HumanMessage(content="你好")]
new = [AIMessage(content="我在")]
print(f"  old（{len(old)} 条）: {[type(m).__name__ for m in old]}")
print(f"  new（{len(new)} 条）: {[type(m).__name__ for m in new]}")
merged = add_messages(old, new)
print(f"  add_messages(old, new) → {len(merged)} 条: "
      f"{[type(m).__name__ for m in merged]}")
print("  ★ 它就是把两个列表接起来")

print()
print("  对比 operator.add（就是 +）：")
print(f"    operator.add([1,2], [3]) = {operator.add([1, 2], [3])}")

print()
print("  add_messages 比 + 多做一件事：id 相同就【替换】，不是追加")
a1 = AIMessage(content="第一版", id="x1")
a2 = AIMessage(content="改过了", id="x1")     # 同一个 id
print(f"    add_messages([a1], [a2]) → "
      f"{[(m.id, m.content) for m in add_messages([a1], [a2])]}")
b1 = AIMessage(content="第一版", id="x1")
b2 = AIMessage(content="另一条", id="x2")     # 不同 id
print(f"    add_messages([b1], [b2]) → "
      f"{[(m.id, m.content) for m in add_messages([b1], [b2])]}")

print()
print("=" * 70)
print("问题3：Annotated 拆开看")
print("=" * 70)
print("  Annotated[list, add_messages]")
print("            ↑      ↑")
print("          类型   合并规则")
print()
print("  跑起来的时候，这一页的值就是普通 list，Annotated 只是贴了张便条")

print()
print("=" * 70)
print("问题4：if not last.tool_calls —— tool_calls 什么时候是空的")
print("=" * 70)
with_tool = AIMessage(content="我看看",
                      tool_calls=[{"name": "bash", "args": {"command": "ls"}, "id": "c1"}])
no_tool = AIMessage(content="任务完成了，我不用再执行命令了。")
for label, m in [("模型调了工具", with_tool), ("模型只说话", no_tool)]:
    print(f"  {label:<12} m.tool_calls = {m.tool_calls}")
    print(f"  {'':<12} not m.tool_calls → {not m.tool_calls}")
    print(f"  {'':<12} 岔路口返回 → "
          f"{'done（结束）' if not m.tool_calls else 'run_tools（去干活）'}")
    print()
