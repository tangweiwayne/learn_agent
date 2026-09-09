"""tc 到底是什么？从模型返回的 message 一层层剥到命令。

运行： python3 tc长什么样.py
改改下面的数据再跑，感受一下。
"""

import json


def 框(t):
    print("\n" + "━" * 66)
    print("  " + t)
    print("━" * 66)


# ══════════════════════════════════════════════════════════
框("① 模型返回的一整条 message —— tc 的老家")

message = {
    "role": "assistant",
    "content": "我先看看 demo.py 的内容。",
    "tool_calls": [
        {
            "id": "call_00_iJEEfbjv",
            "type": "function",
            "function": {"name": "bash", "arguments": '{"command": "nl -ba demo.py"}'},
        }
    ],
}
print(json.dumps(message, ensure_ascii=False, indent=2))


# ══════════════════════════════════════════════════════════
框("② tool_calls 是个列表")

tool_calls = message["tool_calls"]
print(f"\n  type = {type(tool_calls).__name__}    长度 = {len(tool_calls)}")
print("  所以 for tc in tool_calls:  会跑 1 次")


# ══════════════════════════════════════════════════════════
框("③ tc = 列表里的一个元素，只有 3 个键")

tc = tool_calls[0]
print(json.dumps(tc, ensure_ascii=False, indent=2))
print(f"\n  tc 的键 = {list(tc)}")
print("""
     id        回传结果时要带上，一问一答配对
     type      类型标记，永远是 "function"，我们不用
     function  ★ 有用的东西在里面
""")


# ══════════════════════════════════════════════════════════
框("④ 一步一步取")

print(f"\n  tc['function']              = {json.dumps(tc['function'], ensure_ascii=False)}")
print(f"  tc['function']['name']      = {tc['function']['name']!r}     <- 工具名")
print(f"  tc['function']['arguments'] = {tc['function']['arguments']!r}")
print("                                 ^ 是【字符串】，不是字典")
参数 = json.loads(tc["function"]["arguments"])
print(f"\n  json.loads(...)             = {参数}")
print("                                 ^ 现在才是字典")
print(f"  参数['command']             = {参数['command']!r}")


# ══════════════════════════════════════════════════════════
框("⑤ 换成 edit_file，结构一样，内容不同")

tc2 = {
    "id": "call_00_PLiE88g2",
    "type": "function",
    "function": {
        "name": "edit_file",
        "arguments": json.dumps({
            "path": "demo.py",
            "old": "    return a / b",
            "new": '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b',
        }, ensure_ascii=False),
    },
}
print(json.dumps(tc2, ensure_ascii=False, indent=2))

参数2 = json.loads(tc2["function"]["arguments"])
print(f"\n  工具名 = {tc2['function']['name']!r}")
print(f"  参数   = {len(参数2)} 个键 {list(参数2)}")
for k, v in 参数2.items():
    print(f"     参数[{k!r}] = {v!r}")


# ══════════════════════════════════════════════════════════
框("⑥ agent 里那个 for 循环在干什么")

print("""
   for tc in tool_calls:
       工具名 = tc["function"]["name"]
       参数   = self.取出参数(tc)
       observation = self.调用工具(工具名, 参数)
""")
for t in [tc, tc2]:
    名 = t["function"]["name"]
    p = json.loads(t["function"]["arguments"])
    print(f"   tc(name={名!r})  ->  工具名={名!r}  参数={p}")
