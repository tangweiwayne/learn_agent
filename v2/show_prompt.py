"""看清楚：模板文件 → 变量表 → 渲染 → 最终发给模型的提示词

用法： python3 show_prompt.py
"""

from v2_agent import build_agent, render

agent = build_agent(mock=True)
任务 = "修复 buggy.py 的崩溃问题"


def 框(标题):
    print("\n" + "━" * 68)
    print("  " + 标题)
    print("━" * 68)


框("① 磁盘上的模板文件 prompts/instance.txt（原封不动）")
for i, line in enumerate(agent.instance_template.splitlines()[:24], 1):
    标记 = ""
    if "{{" in line:
        标记 = "   ← 有 {{变量}}"
    if "{%" in line:
        标记 = "   ← 有 {% if %}"
    print(f"  {i:2d}| {line}{标记}")
print("  ...")


框("② template_vars() 生成的变量表（一个普通字典）")
v = agent.template_vars(task=任务)
for k, val in v.items():
    print(f"     {k:14s} = {val!r}")


框("③ render(模板, **变量表) 之后 —— 真正发给模型的东西")
渲染后 = render(agent.instance_template, **v)
for i, line in enumerate(渲染后.splitlines()[:24], 1):
    print(f"  {i:2d}| {line}")
print("  ...")


框("④ 逐行对照：模板里的哪一行，变成了结果里的哪一行")
对照 = [
    ("请完成这个任务：{{task}}", "第 1 行"),
    ("6. 完成后单独发一条 `echo {{done_marker}}` 结束", "第 12 行"),
    ("系统：{{system}} {{machine}}", "第 16 行"),
    ("工作目录：{{cwd}}", "第 17 行"),
]
模板行 = agent.instance_template.splitlines()
结果行 = 渲染后.splitlines()
for 原, _ in 对照:
    for i, l in enumerate(模板行):
        if l.strip() == 原.strip():
            print(f"\n  模板 {i+1:2d}| {l}")
            print(f"  结果 {i+1:2d}| {结果行[i]}")
            break

框("⑤ if 块的命运")
print(f"  当前系统: {v['system']}   is_mac={v['is_mac']}  is_linux={v['is_linux']}")
print()
for i, l in enumerate(模板行):
    if "{%" in l or "sed -i" in l:
        print(f"  模板 {i+1:2d}| {l}")
print()
print("  ↓ 渲染后，两个 if 块只留下了匹配当前系统的那个：")
for l in 结果行:
    if "sed" in l:
        print(f"       | {l}")


框("⑥ 最后它去了哪里 —— messages 的第 2 条")
agent.messages = [
    {"role": "system", "content": render(agent.system_template, **v)},
    {"role": "user", "content": 渲染后},
]
for i, m in enumerate(agent.messages):
    print(f"  messages[{i}]  role={m['role']!r}  长度={len(m['content'])} 字符")
print()
print("  这两条就是第 1 步发给 LLM 的全部内容。")
