"""模型怎么知道要那样输出？—— 因为你先发了一张空白表格给它。

运行： python3 怎么规定的.py
"""

import json

print("=" * 68)
print("  第 ① 步：我们发过去一张【空白表格】")
print("=" * 68)

空白表格 = {
    "type": "function",
    "function": {
        "name": "bash",                          # ★ 表格的名字
        "description": "执行一条 bash 命令",       # 什么时候用这张表
        "parameters": {
            "type": "object",
            "properties": {
                "command": {                     # ★ 表格上有一个格子，叫 command
                    "type": "string",            #    这个格子只能填字符串
                    "description": "要执行的 bash 命令",
                }
            },
            "required": ["command"],             # ★ 这个格子必须填
        },
    },
}

请求 = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "看看当前目录有什么"}],
    "tools": [空白表格],          # ← 就是多了这一个字段
}

print(json.dumps(请求, ensure_ascii=False, indent=2))
print("""
  ↑ 翻译成人话：
      "我这儿有一张表，名字叫 bash。
       表上有一个格子叫 command，只能填字符串，而且必须填。
       想执行命令的话，就填这张表。"
""")


print("=" * 68)
print("  第 ② 步：模型还回来一张【填好的表格】")
print("=" * 68)

填好的表格 = {
    "role": "assistant",
    "content": "我先看看目录里有什么。",
    "tool_calls": [
        {
            "id": "call_001",
            "type": "function",
            "function": {
                "name": "bash",                       # ← 对应空表的 name
                "arguments": '{"command": "ls"}',     # ← 对应空表的 properties
            },
        }
    ],
}

print(json.dumps(填好的表格, ensure_ascii=False, indent=2))


print()
print("=" * 68)
print("  两张表的字段，一一对应")
print("=" * 68)

f空 = 空白表格["function"]
f填 = 填好的表格["tool_calls"][0]["function"]
填的内容 = json.loads(f填["arguments"])

print(f"""
   空白表格里写的                          模型填回来的
   ────────────────────────────────       ────────────────────────
   name: {f空['name']!r:<26}   →   name: {f填['name']!r}
   properties 里有个格子叫 'command'   →   arguments 里有个键叫 'command'
   它的 type 是 'string'               →   它的值是 {填的内容['command']!r}  ({type(填的内容['command']).__name__})
   required: {f空['parameters']['required']}                    →   确实填了，没漏
""")

print("=" * 68)
print("  为什么模型会乖乖照填？三个原因")
print("=" * 68)
print("""
   1. 它被【专门训练过】这套格式 —— 训练数据里有海量的工具调用样本，
      比"用文字模仿 ```bash 代码块"熟练得多

   2. API 服务端会【校验】—— 你写了 type: string，它填了数字，
      服务端那层就会纠正或报错，不会一路传到你这儿

   3. 这是【结构化生成】—— 模型生成 tool_calls 时走的是受约束的路径，
      不是自由发挥写文章
""")

print("=" * 68)
print("  想加第二张表？往列表里再放一个就行")
print("=" * 68)

第二张表 = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "把文件里的一段旧文本换成新文本",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "old": {"type": "string", "description": "要被替换的旧文本"},
                "new": {"type": "string", "description": "替换成的新文本"},
            },
            "required": ["path", "old", "new"],
        },
    },
}

for t in [空白表格, 第二张表]:
    f = t["function"]
    格子 = list(f["parameters"]["properties"])
    print(f"   表名 {f['name']:12s} 格子: {格子}")

print("""
   模型看到两张表，会【自己判断】这一步该填哪张 ——
   靠的就是 description 那句话。这是下一步"多工具"要做的事。
""")
