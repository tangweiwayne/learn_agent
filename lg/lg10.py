"""① fn 到底长什么样  ② invoke 会检查参数  ③ bind_tools 挂了什么

跑法：  python3 lg10.py     （不联网、不花钱；用的是假 key，只看结构不发请求）
"""
import json

from langchain_core.tools import tool


@tool
def edit_file(path: str, old: str, new: str) -> str:
    """把文件里的一段文字换成另一段。"""
    return f"（改了 {path}）"


TOOLS_BY_NAME = {"edit_file": edit_file}
fn = TOOLS_BY_NAME.get("edit_file")

print("=" * 74)
print("① fn 的【真面目】—— 直接 print 出来")
print("=" * 74)
print("  print(fn)  →")
print(f"     {fn}")
print()
print(f"  type(fn)   →  {type(fn)}")
print()
print("  它就是一个对象，里面装了 4 样东西：")
print(f"     fn.name        = {fn.name!r}")
print(f"     fn.description = {fn.description!r}")
print(f"     fn.args        = {json.dumps(fn.args, ensure_ascii=False)}")
print(f"     fn.func        = {fn.func}   ← 你原来写的那个函数，被收在这儿")
print()
print("  ★ fn.func 就是没加 @tool 时的原函数，可以直接括号调用：")
print(f"     fn.func('a.py', 'x', 'y')                        → "
      f"{fn.func('a.py', 'x', 'y')!r}")
print(f"     fn.invoke({{'path':'a.py','old':'x','new':'y'}})    → "
      f"{fn.invoke({'path': 'a.py', 'old': 'x', 'new': 'y'})!r}")
print("     两条路通向同一个函数，只是入口形式不同。")

print()
print("=" * 74)
print("② invoke 会替你【检查参数】—— 这是普通函数没有的")
print("=" * 74)
cases = [
    ("参数齐全", {"path": "a.py", "old": "x", "new": "y"}),
    ("少一个 new", {"path": "a.py", "old": "x"}),
    ("多一个没定义的", {"path": "a.py", "old": "x", "new": "y", "junk": 1}),
    ("类型不对（path 给数字）", {"path": 123, "old": "x", "new": "y"}),
]
for label, kwargs in cases:
    try:
        r = fn.invoke(kwargs)
        print(f"  {label:<24} → {r!r}")
    except Exception as e:
        msg = str(e).replace("\n", " ")[:88]
        print(f"  {label:<24} → ❌ {type(e).__name__}: {msg}")

print()
print("=" * 74)
print("③ bind_tools 到底把什么挂到了模型上")
print("=" * 74)
from langchain_openai import ChatOpenAI


@tool
def bash(command: str) -> str:
    """在电脑上执行一条 bash 命令，返回标准输出和错误输出。"""
    return ""


base = ChatOpenAI(model="deepseek-chat", api_key="sk-假的",
                  base_url="https://api.deepseek.com/v1")
bound = base.bind_tools([bash, edit_file])

print(f"  base  的类型 = {type(base).__name__}")
print(f"  bound 的类型 = {type(bound).__name__}   ← 变成了另一个类")
print()
print("  ★ bind_tools 没有改 base，它造了一个【新对象】：")
print(f"     base is bound ? {base is bound}")
print()
print("  bound.kwargs 里存的就是【每次请求都会带上的额外字段】：")
print(f"     bound.kwargs.keys() = {list(bound.kwargs.keys())}")
print()
print("  bound.kwargs['tools'] 就是发给 API 的那段 JSON：")
print("     " + json.dumps(bound.kwargs["tools"], ensure_ascii=False,
                           indent=2).replace("\n", "\n     "))

print()
print("=" * 74)
print("④ 同一个 base，可以绑出好几个不同工具集的模型")
print("=" * 74)
main_llm = base.bind_tools([bash, edit_file])
sub_llm = base.bind_tools([bash])
print(f"  main_llm 带的工具: {[t['function']['name'] for t in main_llm.kwargs['tools']]}")
print(f"  sub_llm  带的工具: {[t['function']['name'] for t in sub_llm.kwargs['tools']]}")
print(f"  base 自己        : 没有 tools → {getattr(base, 'kwargs', {})}")
