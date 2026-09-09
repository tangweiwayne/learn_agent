"""
v3 · 改动 2：多工具

工具定义 + 工具实现 + 分派，全放这个文件。

分工：
  bash       —— 看（cat/nl/grep）和跑（python/pytest），什么都能干
  edit_file  —— 只负责精确改文件，不做别的
"""

import os

# ==================================================================
# 工具 1：bash
# ==================================================================
BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "在用户的电脑上执行一条 bash 命令，返回标准输出和错误输出。"
            "用它来【查看】文件（cat / nl -ba / grep / head）、【搜索】、"
            "【运行】程序和测试。"
            "注意：修改已有文件时请优先用 edit_file 工具，不要用 cat > 重写整个文件。"
            "每条命令都在new_s的子进程里执行，cd 和环境变量不会keep到next_text。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的完整 bash 命令，可以是多行",
                }
            },
            "required": ["command"],
        },
    },
}


# ==================================================================
# 工具 2：edit_file
# ==================================================================
EDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "把文件里的一段old_s文本精确替换成new_s文本。"
            "修改已有文件时【优先用这个】，不要用 bash 的 cat > 重写整个文件 —— "
            "那样又费 token 又容易改错别的地方。"
            "要求：old 必须在文件里【恰好出现一次】。"
            "如果不确定，先用 bash 的 `nl -ba 文件名` 看清楚原文再来。"
            "new_s建文件请用 bash 的 cat > 。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件fpath，相对于当前工作tmpdir",
                },
                "old": {
                    "type": "string",
                    "description": (
                        "要被替换的old_s文本，必须和文件里的content【逐字符一致】"
                        "（包括缩进和换行），并且在文件里恰好出现一次"
                    ),
                },
                "new": {
                    "type": "string",
                    "description": "替换成的new_s文本",
                },
            },
            "required": ["path", "old", "new"],
        },
    },
}


# ==================================================================
# 工具 3：update_plan  —— 让模型先列计划，再照着做
# ==================================================================
PLAN_TOOL = {
    "type": "function",
    "function": {
        "name": "update_plan",
        "description": (
            "创建或更新任务计划。"
            "【开工之前必须先调用一次】把任务拆成 2~6 个具体、可验证的步骤。"
            "之后每做完一步就再调用一次，把那一步的 status 改成 done、"
            "下一步改成 doing。steps 每次都要【完整传全部步骤】，不是只传变化的那条。"
            "只做计划里的事；确实需要加新步骤时，重新调用并说明理由。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "这一步要做什么，一句话，具体可验证",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["todo", "doing", "done"],
                                "description": "todo=还没做  doing=正在做  done=做完了",
                            },
                        },
                        "required": ["text", "status"],
                    },
                    "description": "完整的计划，每一步一个对象",
                }
            },
            "required": ["steps"],
        },
    },
}


# ==================================================================
# 工具 4：task —— 派一个子助手去查，只要结论
# ==================================================================
TASK_TOOL = {
    "type": "function",
    "function": {
        "name": "task",
        "description": (
            "派一个独立的助手去完成一个【只读的调查任务】，它会自己跑几步，"
            "然后只把结论返回给你，中间翻过的那些长输出【不会】进入你的对话。"
            "适合：在陌生目录里定位某个功能在哪个文件、"
            "搞清楚一个报错的根因、摸清一个项目的结构。"
            "不适合：修改文件或跑会改动东西的命令 —— 那些你自己用 edit_file / bash 做，"
            "因为助手改了什么你看不见。"
            "重要：助手【看不到】你和用户的对话，"
            "所以 prompt 里要把目录、文件名、背景一次讲全，不能说“继续刚才那个”。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "交给助手的完整任务描述，必须自包含。",
                },
            },
            "required": ["prompt"],
        },
    },
}


# ==================================================================
# 工具 5：report —— 子助手【交报告】的唯一出口
# ==================================================================
REPORT_TOOL = {
    "type": "function",
    "function": {
        "name": "report",
        "description": (
            "提交你的最终调查报告并结束。这是你结束任务的【唯一】方式。"
            "只在你真的查完、能给出确定结论时调用一次。"
            "如果查下来发现【问题不存在】或【任务的前提和事实不符】，"
            "也用它如实汇报，不要继续找。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": (
                        "完整的结论，用中文写。主助手【只能看到这段文字】，"
                        "看不到你跑过的任何命令和输出。所以文件名、行号、函数名、"
                        "关键代码片段都要直接写进来，不能说“见上面的输出”。"
                    ),
                },
                "confident": {
                    "type": "string",
                    "enum": ["yes", "partial", "no"],
                    "description": "你对这个结论有多确定：yes=查实了；partial=部分查实；no=没查出来。",
                },
            },
            "required": ["summary", "confident"],
        },
    },
}


# 主 agent 能用的全套
ALL_TOOLS = [PLAN_TOOL, TASK_TOOL, BASH_TOOL, EDIT_TOOL]

# 子助手能用的：只有 bash，没有 edit_file（不许改），没有 task（不许再派）
SUBAGENT_TOOLS = [REPORT_TOOL, BASH_TOOL]


def render_plan(steps: list) -> str:
    """把计划渲染成给模型看的清单。

    输入 steps 形如：
        [{"text": "读文件", "status": "done"},
         {"text": "改代码", "status": "doing"},
         {"text": "验证",   "status": "todo"}]
    """
    if not steps:
        return "<plan>（还没有计划）</plan>"

    MARK = {"done": "[x]", "doing": "[>]", "todo": "[ ]"}
    lines = ["<plan>"]
    for i, item in enumerate(steps, 1):
        mark = MARK.get(item.get("status"), "[ ]")
        lines.append(f"  {mark} {i}. {item.get('text', '')}")
    lines.append("</plan>")

    pending = [it for it in steps if it.get("status") != "done"]
    if not pending:
        lines.append("全部完成 —— 可以结束了，不要再加新步骤。")
    else:
        next_text = pending[0].get("text", "")
        lines.append(f"还剩 {len(pending)} 步。下一步：{next_text}。只做这一条，别的先不碰。")
    return "\n".join(lines)


def normalize_plan(steps) -> list:
    """把模型可能填出的各种形状，规范成 [{"text":..., "status":...}]。

    好的防御不是"硬转成能用的类型"，而是"识别实际格式并规范化"。
    见过的形状：
        ["读文件", "改代码"]                              纯字符串数组
        [{"text": "读文件", "status": "done"}]            标准格式
        [{"steps": "读文件", "completed": 1}]             模型自创的
        [{"content": "读文件", "status": "completed"}]    别的常见叫法
    """
    TEXT_KEYS = ("text", "steps", "step", "content", "title", "task", "description")
    STATUS_KEYS = ("status", "state")
    DONE_WORDS = {"done", "completed", "complete", "finished", "true", "1"}
    DOING_WORDS = {"doing", "in_progress", "active", "current", "running"}

    out = []
    for item in steps or []:
        if isinstance(item, str):
            out.append({"text": item, "status": "todo"})
            continue
        if not isinstance(item, dict):
            out.append({"text": str(item), "status": "todo"})
            continue

        text = ""
        for k in TEXT_KEYS:
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                text = v.strip()
                break
        if not text:
            text = str(item)

        status = "todo"
        for k in STATUS_KEYS:
            v = item.get(k)
            if isinstance(v, str):
                low = v.strip().lower()
                if low in DONE_WORDS:
                    status = "done"
                elif low in DOING_WORDS:
                    status = "doing"
                break
        else:
            # 没有 status，看看有没有 completed 之类的布尔/数字
            c = item.get("completed")
            if c is True or (isinstance(c, (int, float)) and c > 0):
                status = "done"

        out.append({"text": text, "status": status})
    return out


# ==================================================================
# edit_file 的实现
# ==================================================================
def edit_file(path: str, old: str, new: str, cwd: str = "") -> str:
    """精确替换。返回给模型看的结果文本。

    失败时不抛异常，而是返回一段【能指导模型怎么改】的说明。
    """
    full_path = os.path.join(cwd or os.getcwd(), path)

    if not os.path.exists(full_path):
        return (f"<error>文件不存在：{path}</error>\n"
                f"提示：先用 bash 的 `ls` 确认路径；新建文件请用 bash 的 `cat > {path}`。")

    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    count = content.count(old)

    if count == 0:
        return (f"<error>在 {path} 里找不到这段文本</error>\n"
                f"你要找的是：\n{old!r}\n"
                f"提示：old 必须和文件内容【逐字符一致】，包括缩进和换行。"
                f"请先用 `nl -ba {path}` 看清原文，再照抄过来。")

    if count > 1:
        return (f"<error>这段文本在 {path} 里出现了 {count} 次，不知道该改哪一处</error>\n"
                f"提示：请在 old 里多带几行上下文，让它变得唯一。")

    new_content = content.replace(old, new, 1)      # 只替换 1 次
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    line_no = content[: content.index(old)].count("\n") + 1
    return (f"<success>已修改 {path}（第 {line_no} 行附近）</success>\n"
            f"<removed>\n{old}\n</removed>\n"
            f"<added>\n{new}\n</added>")


# ==================================================================
if __name__ == "__main__":
    import tempfile

    print("=" * 66)
    print("=== normalize_plan：模型填什么形状都能规范化 ===")
    print("=" * 66)
    samples = [
        ("纯字符串数组（我们原本期望的）", ["读文件", "改代码", "验证"]),
        ("标准格式", [{"text": "读文件", "status": "done"},
                     {"text": "改代码", "status": "doing"}]),
        ("模型自创的（buggy6 那次）", [{"steps": "读文件", "completed": 1},
                                    {"steps": "改代码", "completed": 0}]),
        ("别的常见叫法", [{"content": "读文件", "status": "completed"},
                        {"content": "改代码", "status": "in_progress"}]),
    ]
    for label, raw in samples:
        print(f"\n  ▼ {label}")
        print(f"     输入: {raw}")
        p = normalize_plan(raw)
        print(f"     规范化后: {p}")
        print("     渲染:")
        for l in render_plan(p).splitlines():
            print("        " + l)

    print("\n" + "=" * 66)
    print("=== edit_file 四种情况 ===")
    print("=" * 66)
    tmpdir = tempfile.mkdtemp(prefix="edittest_")
    fpath = os.path.join(tmpdir, "demo.py")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")

    print("\n  ① 正常替换")
    print(edit_file("demo.py", "    return a / b",
                    '    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b',
                    cwd=tmpdir))
    print("\n  ② 找不到 old")
    print(edit_file("demo.py", "return a * b", "xxx", cwd=tmpdir))
    print("\n  ③ 出现多次")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("x = 1\ny = 1\nz = 1\n")
    print(edit_file("demo.py", "= 1", "= 2", cwd=tmpdir))
    print("\n  ④ 文件不存在")
    print(edit_file("不存在.py", "a", "b", cwd=tmpdir))
