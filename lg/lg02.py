"""笔记本到底怎么被更新的：四种写法对比。

跑法：  python3 lg02.py     （不联网、不花钱）
"""
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


def run(title, StateCls, node):
    print("=" * 66)
    print(title)
    print("=" * 66)
    b = StateGraph(StateCls)
    b.add_node("n", node)
    b.add_edge(START, "n")
    b.add_edge("n", END)
    app = b.compile()
    before = {"number": 5, "history": [1, 2, 3]}
    print(f"  跑之前  {before}")
    after = app.invoke(before)
    print(f"  跑之后  {after}\n")


class S1(TypedDict):
    number: int
    history: list


def n1(state):
    print(f"  工位返回  {{'number': {state['number']+3}}}")
    return {"number": state["number"] + 3}


run("写法1：返回里没有 history → 那一页原封不动", S1, n1)


def n2(state):
    print(f"  工位返回  {{'number': {state['number']+3}, 'history': [{state['number']+3}]}}")
    return {"number": state["number"] + 3, "history": [state["number"] + 3]}


run("写法2：返回 history=[新值] → 【整页被覆盖】，老的没了", S1, n2)


def n3(state):
    new = state["number"] + 3
    print(f"  工位返回  {{'number': {new}, 'history': {state['history']} + [{new}]}}")
    return {"number": new, "history": state["history"] + [new]}


run("写法3：state['history'] + [新值] → 自己把老的抄一遍再加新的", S1, n3)


class S2(TypedDict):
    number: int
    history: Annotated[list, operator.add]      # ★ 差别只在这一行


def n4(state):
    new = state["number"] + 3
    print(f"  工位返回  {{'number': {new}, 'history': [{new}]}}   ← 只给新的")
    return {"number": new, "history": [new]}


run("写法4：加了 Annotated[list, operator.add] → 它自己会拼", S2, n4)
