"""慢镜头：装饰器是什么 → @tool 之后 bash 变成什么 → 怎么被调用。

跑法：  python3 lg09.py     （不联网、不花钱）
"""
import json

from langchain_core.tools import tool

print("=" * 72)
print("第1步：先看什么是【装饰器】—— 用一个自己写的，和 langchain 无关")
print("=" * 72)


def wrap(original):
    """这就是一个装饰器：收一个函数，返回一个新东西。"""
    def wrapped(*args, **kwargs):
        print("      （包装说：我要开始调用原函数了）")
        result = original(*args, **kwargs)
        print("      （包装说：原函数返回了）")
        return result
    return wrapped


@wrap
def greet(name):
    print(f"      你好，{name}")
    return "打完了"


print("  写了 @wrap 之后，调用 greet('小明')：")
r = greet("小明")
print(f"  返回值 = {r!r}")
print()
print("  ★ @wrap 完全等于下面这一行：")
print("       greet = wrap(greet)")
print("  ★ 所以 greet 已经不是你写的那个函数了，是被换掉的新东西")

print()
print("=" * 72)
print("第2步：@tool 也是装饰器，它把函数换成了一个【对象】")
print("=" * 72)


def bash_plain(command: str) -> str:
    """在电脑上执行一条 bash 命令。"""
    return f"（假装执行了：{command}）"


@tool
def bash(command: str) -> str:
    """在电脑上执行一条 bash 命令。"""
    return f"（假装执行了：{command}）"


print(f"  没加 @tool ：type = {type(bash_plain).__name__}")
print(f"  加了 @tool ：type = {type(bash).__name__}")
print()
print("  加了之后能问它这些（普通函数问不了）：")
print(f"     bash.name        = {bash.name!r}")
print(f"     bash.description = {bash.description!r}")
print(f"     bash.args        = {json.dumps(bash.args, ensure_ascii=False)}")

print()
print("=" * 72)
print("第3步：怎么调用它")
print("=" * 72)
print("  没加 @tool 的普通函数：直接括号，参数一个个传")
print(f"     bash_plain('ls -la')  →  {bash_plain('ls -la')!r}")
print()
print("  加了 @tool 的对象：用 .invoke()，参数装在一个【字典】里")
print(f"     bash.invoke({{'command': 'ls -la'}})  →  {bash.invoke({'command': 'ls -la'})!r}")
print()
print("  为什么要字典？因为模型给你的就是字典：")
tc = {"name": "bash", "args": {"command": "ls -la"}, "id": "call_1"}
print(f"     模型返回的 tool_call = {tc}")
print(f"     里面的 args           = {tc['args']}     ← 正好能直接喂给 invoke")

print()
print("=" * 72)
print("第4步：多个工具时，怎么按名字找到对的那个")
print("=" * 72)


@tool
def edit_file(path: str, old: str, new: str) -> str:
    """把文件里的一段文字换成另一段。"""
    return f"（假装把 {path} 里的 {old!r} 换成了 {new!r}）"


TOOLS = [bash, edit_file]
print("  TOOLS = [bash, edit_file]")
print()
print("  建一张名字→工具的对照表：")
print("     TOOLS_BY_NAME = {t.name: t for t in TOOLS}")
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
for k, v in TOOLS_BY_NAME.items():
    print(f"       {k!r:<14} → <工具 {v.name}，参数 {list(v.args)}>")

print()
print("=" * 72)
print("第5步：完整走一遍（模型说要调 → 查表 → 执行）")
print("=" * 72)
from_model = [
    {"name": "bash", "args": {"command": "nl -ba discount.py"}, "id": "call_1"},
    {"name": "edit_file",
     "args": {"path": "discount.py", "old": "a", "new": "b"}, "id": "call_2"},
    {"name": "不存在的工具", "args": {}, "id": "call_3"},
]
for tc in from_model:
    print(f"\n  模型说要调：{tc['name']}，参数 {tc['args']}")
    fn = TOOLS_BY_NAME.get(tc["name"])
    print(f"     查表 TOOLS_BY_NAME.get({tc['name']!r}) → "
          f"{('<工具 ' + fn.name + '>') if fn else None}")
    if fn:
        observation = fn.invoke(tc["args"])
    else:
        observation = f"<error>没有叫 {tc['name']} 的工具</error>"
    print(f"     执行结果 = {observation!r}")
