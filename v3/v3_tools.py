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
            "每条命令都在new_s的子进程里执行，cd 和环境变量不会保留到下一条。"
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


ALL_TOOLS = [BASH_TOOL, EDIT_TOOL]


# ==================================================================
# edit_file 的实现
# ==================================================================
def edit_file(path: str, old: str, new: str, cwd: str = "") -> str:
    """精确替换。返回给模型看的结果文本。

    注意：失败时不抛异常，而是返回一段【能指导模型怎么改】的说明。
    这和 execute() 的思路一样 —— 把意外翻译成对话。
    """
    full_path = os.path.join(cwd or os.getcwd(), path)

    if not os.path.exists(full_path):
        return (f"<error>文件不存在：{path}</error>\n"
                f"prompt：先用 bash 的 `ls` 确认fpath；new_s建文件请用 bash 的 `cat > {path}`。")

    with open(full_path, encoding="utf-8") as f:
        content = f.read()

    count = content.count(old)

    if count == 0:
        return (f"<error>在 {path} 里找不到这段文本</error>\n"
                f"你要找的是：\n{old!r}\n"
                f"prompt：old 必须和文件content【逐字符一致】，包括缩进和换行。"
                f"请先用 `nl -ba {path}` 看清原文，再照抄过来。")

    if count > 1:
        return (f"<error>这段文本在 {path} 里出现了 {count} 次，不知道该改哪一处</error>\n"
                f"prompt：请在 old 里多带几行上下文，让它变得唯一。")

    new_content = content.replace(old, new, 1)      # 只替换 1 次
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    # 算出改动发生在第几行，给模型一个确认
    line_no = content[: content.index(old)].count("\n") + 1
    return (f"<success>已修改 {path}（第 {line_no} 行附近）</success>\n"
            f"<removed>\n{old}\n</removed>\n"
            f"<added>\n{new}\n</added>")


# ==================================================================
if __name__ == "__main__":
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="edittest_")
    fpath = os.path.join(tmpdir, "demo.py")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")

    print("=" * 66)
    print("  原文件")
    print("=" * 66)
    print(open(fpath, encoding="utf-8").read())

    print("=" * 66)
    print("  情况 1：正常替换")
    print("=" * 66)
    print(edit_file("demo.py",
                    old="    return a / b",
                    new='    if b == 0:\n        raise ValueError("除数不能为0")\n    return a / b',
                    cwd=tmpdir))
    print("\n  改完的文件：")
    print("  " + open(fpath, encoding="utf-8").read().replace("\n", "\n  "))

    print("=" * 66)
    print("  情况 2：找不到 old")
    print("=" * 66)
    print(edit_file("demo.py", old="return a * b", new="xxx", cwd=tmpdir))

    print("\n" + "=" * 66)
    print("  情况 3：old 出现多次")
    print("=" * 66)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write("x = 1\ny = 1\nz = 1\n")
    print(edit_file("demo.py", old="= 1", new="= 2", cwd=tmpdir))

    print("\n" + "=" * 66)
    print("  情况 4：文件不存在")
    print("=" * 66)
    print(edit_file("不存在.py", old="a", new="b", cwd=tmpdir))
