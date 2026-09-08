"""看看 agent 跑完之后，messages 列表长成什么样。

用法： python3 show_messages.py
"""

from v1_loop import make_mock_model, run

msgs = run("统计当前目录有多少个 .py 文件", model=make_mock_model())

print()
print("=" * 60)
print(f"总共 {len(msgs)} 条消息：")
print("=" * 60)

for i, m in enumerate(msgs):
    role = m["role"]
    content = m["content"].replace("\n", "\\n")     # 换行显示成 \n，一行一条
    if len(content) > 45:
        content = content[:45] + "…"
    print(f"[{i}] {role:10s} {content}")
