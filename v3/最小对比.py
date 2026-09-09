"""v3 和 v2 唯一的区别：命令怎么交到我们手上。

运行： python3 最小对比.py
"""

import json
import re

print("场景：模型想让我们执行 `ls` 这条命令。")
print("     两种版本里，模型把这条命令'交'给我们的方式不一样。")


# ══════════════════════════════════════════════════════════════════
print("\n" + "═" * 62)
print("  v2：模型给我们一段话，命令埋在里面")
print("═" * 62)

v2给我们的 = "我先看看目录里有什么。\n\n```bash\nls\n```"

print("\n模型给的东西（一个字符串）：")
print(f"   {v2给我们的!r}")

print("\n我们要自己把命令挖出来：")
blocks = re.findall(r"```bash\n(.*?)\n```", v2给我们的, re.DOTALL)
print(f"   blocks = re.findall(...)   →   {blocks}")
print(f"   命令   = blocks[0]         →   {blocks[0]!r}")


# ══════════════════════════════════════════════════════════════════
print("\n" + "═" * 62)
print("  v3：模型给我们一张填好的表格")
print("═" * 62)

v3给我们的 = {
    "content": "我先看看目录里有什么。",
    "tool_calls": [
        {
            "id": "call_001",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": '{"command": "ls"}',
            },
        }
    ],
}

print("\n模型给的东西（一个字典）：")
print("   " + json.dumps(v3给我们的, ensure_ascii=False, indent=2).replace("\n", "\n   "))

print("\n我们直接去取那一格：")
第一张表 = v3给我们的["tool_calls"][0]
print("   第一张表 = v3给我们的['tool_calls'][0]")
表格内容 = 第一张表["function"]["arguments"]
print(f"   表格内容 = 第一张表['function']['arguments']   ->   {表格内容!r}")
print("              ^ 注意它是个字符串，还要拆一层")
拆开了 = json.loads(表格内容)
print(f"   拆开了   = json.loads(表格内容)                ->   {拆开了}")
print(f"   命令     = 拆开了['command']                   ->   {拆开了['command']!r}")


# ══════════════════════════════════════════════════════════════════
print("\n" + "═" * 62)
print("  两边都拿到了 'ls'，区别在【怎么拿到的】")
print("═" * 62)
print("""
   v2：  一段话  --用正则去找-->  'ls'
                    ^ 可能找不到、找错、找出好几个

   v3：  一个字典 --按键名去取-->  'ls'
                    ^ 位置固定，取就完了
""")
