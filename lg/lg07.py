"""工具定义：你手写 JSON Schema vs @tool 自动生成。

跑法：  python3 lg07.py     （不联网、不花钱）
"""
import json

from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool

# ============ 你的 v3_tools.py 里手写的 ============
V3_BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "在电脑上执行一条 bash 命令，返回标准输出和错误输出。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的完整 bash 命令"},
            },
            "required": ["command"],
        },
    },
}


# ============ LangChain 的写法：函数 + 一个装饰器 ============
@tool
def bash(command: str) -> str:
    """在电脑上执行一条 bash 命令，返回标准输出和错误输出。"""
    return "（这里是真正执行的代码）"


print("=" * 72)
print("① @tool 把普通函数变成了什么")
print("=" * 72)
print(f"  type(bash)        = {type(bash).__name__}")
print(f"  bash.name         = {bash.name!r}          ← 从函数名来的")
print(f"  bash.description  = {bash.description!r}   ← 从 docstring 来的")
print(f"  bash.args         = {json.dumps(bash.args, ensure_ascii=False)}")
print("                                             ↑ 从函数签名 command: str 来的")

print()
print("=" * 72)
print("② 发给 API 的时候，它变成这个（和你手写的对比）")
print("=" * 72)
generated = convert_to_openai_tool(bash)
print("  @tool 自动生成：")
print("     " + json.dumps(generated, ensure_ascii=False, indent=2).replace("\n", "\n     "))
print()
print("  你手写的：")
print("     " + json.dumps(V3_BASH_TOOL, ensure_ascii=False, indent=2).replace("\n", "\n     "))

print()
print("=" * 72)
print("③ 三样东西的来源")
print("=" * 72)
print("""
    @tool
    def bash(command: str) -> str:
        \"\"\"在电脑上执行一条 bash 命令，返回标准输出和错误输出。\"\"\"
         │        │
         │        └──→ description（模型靠它决定什么时候用这个工具）
         └──→ name

    def bash(command: str)
             │        │
             │        └──→ "type": "string"
             └──→ "properties" 里的键名 + "required"
""")

print("=" * 72)
print("④ 工具是可以直接调的（不经过模型）")
print("=" * 72)
print(f"  bash.invoke({{'command': 'ls'}})  →  {bash.invoke({'command': 'ls'})!r}")
