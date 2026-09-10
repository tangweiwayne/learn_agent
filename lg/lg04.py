"""消息：你的字典 vs LangGraph 的对象 —— 把两边摆一起看。

跑法：  python3 lg04.py     （不联网、不花钱）
"""
import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

print("=" * 72)
print("① 系统消息")
print("=" * 72)
mine = {"role": "system", "content": "你是一个能操作电脑的助手。"}
theirs = SystemMessage(content="你是一个能操作电脑的助手。")
print(f"  你的 v3 :  {mine}")
print(f"  LangGraph:  {theirs!r}")
print(f"  取内容    :  你的 → m['content']   = {mine['content']!r}")
print(f"              它的 → m.content       = {theirs.content!r}")

print()
print("=" * 72)
print("② 用户消息")
print("=" * 72)
mine = {"role": "user", "content": "请修好 main.py"}
theirs = HumanMessage(content="请修好 main.py")
print(f"  你的 v3 :  {mine}")
print(f"  LangGraph:  {theirs!r}")

print()
print("=" * 72)
print("③ 模型回复（带工具调用）—— 差别最大的就是这个")
print("=" * 72)
mine = {
    "role": "assistant",
    "content": "我先看看目录。",
    "tool_calls": [{
        "id": "call_1",
        "type": "function",
        "function": {"name": "bash", "arguments": '{"command": "ls -la"}'},
    }],
}
theirs = AIMessage(
    content="我先看看目录。",
    tool_calls=[{"name": "bash", "args": {"command": "ls -la"}, "id": "call_1"}],
)
print("  你的 v3（一个嵌套字典）：")
print("     " + json.dumps(mine, ensure_ascii=False, indent=2).replace("\n", "\n     "))
print()
print("  LangGraph：")
print(f"     content     = {theirs.content!r}")
print(f"     tool_calls  = {theirs.tool_calls}")

print()
print("  ★ 想拿到命令字符串，两边各要写什么：")
print("     你的  ：json.loads(m['tool_calls'][0]['function']['arguments'])['command']")
print(f"             → {json.loads(mine['tool_calls'][0]['function']['arguments'])['command']!r}")
print("     它的  ：m.tool_calls[0]['args']['command']")
print(f"             → {theirs.tool_calls[0]['args']['command']!r}")

print()
print("=" * 72)
print("④ 工具结果")
print("=" * 72)
mine = {"role": "tool", "tool_call_id": "call_1", "content": "<returncode>0</returncode>"}
theirs = ToolMessage(content="<returncode>0</returncode>", tool_call_id="call_1")
print(f"  你的 v3 :  {mine}")
print(f"  LangGraph:  {theirs!r}")

print()
print("=" * 72)
print("⑤ 它其实就是个带字段的对象，可以随便看")
print("=" * 72)
m = AIMessage(content="嗨", tool_calls=[{"name": "bash", "args": {"command": "ls"}, "id": "c1"}])
print(f"  type(m)          = {type(m).__name__}")
print(f"  m.content        = {m.content!r}")
print(f"  m.tool_calls     = {m.tool_calls}")
print(f"  m.id             = {m.id}")
print()
print("  转回你熟悉的字典：m.model_dump() 挑几个键 →")
d = m.model_dump()
for k in ["type", "content", "tool_calls", "id"]:
    print(f"     {k:<12} = {d.get(k)}")
