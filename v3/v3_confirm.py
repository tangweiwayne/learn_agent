"""
v3 · ConfirmAgent：多工具版的确认闸门

和 v2 的差别：v2 只有 bash 一个工具，重写 execute_action 就够了。
现在有两个工具，改成重写【分派方法】call_tool()，这样每个工具都能管到。
"""

import re

from v3_agent import Agent, build_agent

# 白名单：只读命令，直接放行不打扰
SAFE_PATTERNS = [
    r"^ls(\s|$)", r"^pwd$", r"^cd\s+\S+$",
    r"^cat\s+\S+$", r"^head\s", r"^tail\s", r"^nl\s", r"^wc(\s|$)",
    r"^grep\s", r"^find\s", r"^which\s", r"^echo\s+\S+$",
    r"^git\s+(status|diff|log|branch)(\s|$)",
    r"^python3?\s+--version$",
]

# 出现这些符号说明可能在写文件或嵌套执行，一律不放行
DANGER_SIGNS = [">", ";", "`", "$("]


class ConfirmAgent(Agent):
    def __init__(self, *args, mode="confirm", whitelist=None, ask=input, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.whitelist = SAFE_PATTERNS if whitelist is None else whitelist
        self.ask = ask             # 每次工具调用的确认闸门
        self.ask_human = ask       # 被 Ctrl-C 打断时问话，用同一个函数
        self.rejected = 0

    # ---------- 只对 bash 做白名单判断 ----------
    def is_safe(self, command: str) -> bool:
        if "\n" in command:
            return False
        if any(s in command for s in DANGER_SIGNS):
            return False
        segments = [s.strip() for s in re.split(r"&&|\|\||\|", command) if s.strip()]
        return bool(segments) and all(
            any(re.search(p, seg) for p in self.whitelist) for seg in segments
        )

    def subagent_kwargs(self) -> dict:
        """把确认闸门传给子助手 —— 否则子助手的 bash 一路畅通无阻。"""
        return {"mode": self.mode, "whitelist": self.whitelist, "ask": self.ask}

    # ---------- 把一次工具调用描述给人看 ----------
    def describe_call(self, tool_name: str, args: dict) -> str:
        if tool_name == "update_plan":
            from v3_tools import normalize_plan
            plan = normalize_plan(args.get("steps") or [])
            done = sum(1 for it in plan if it["status"] == "done")
            MARK = {"done": "[x]", "doing": "[>]", "todo": "[ ]"}
            return f"计划（已完成 {done}/{len(plan)}）：\n" + "\n".join(
                f"    {MARK.get(it['status'], '[ ]')} {i}. {it['text']}"
                for i, it in enumerate(plan, 1))
        if tool_name == "task":
            return f"派子助手去查：\033[1m{args.get('prompt', '')}\033[0m"
        if tool_name == "bash":
            return f"\033[1m{args.get('command', '')}\033[0m"
        if tool_name == "edit_file":
            return (f"修改文件 \033[1m{args.get('path')}\033[0m\n"
                    f"    \033[31m- {args.get('old', '')}\033[0m\n"
                    f"    \033[32m+ {args.get('new', '')}\033[0m")
        return f"{tool_name}({args})"

    # ▼▼▼ 全部改动就是重写这一个方法 ▼▼▼
    def call_tool(self, tool_name: str, args: dict) -> str:
        if self.mode == "yolo":
            return super().call_tool(tool_name, args)

        # bash 且命中白名单 → 不打扰
        if tool_name == "bash" and self.is_safe(args.get("command", "")):
            self.say(f"  ✓ 白名单放行: {args.get('command')}", "\033[90m")
            return super().call_tool(tool_name, args)

        answer = self.ask(
            f"\n\033[43m\033[30m 需要确认 \033[0m 即将执行 \033[36m{tool_name}\033[0m：\n"
            f"    {self.describe_call(tool_name, args)}\n"
            f"  [y]执行  [n]拒绝  [a]以后都别问  > "
        ).strip().lower()

        if answer == "a":
            self.mode = "yolo"
            self.say("  → 切换到 yolo 模式，后面不再询问", "\033[33m")
            return super().call_tool(tool_name, args)

        if answer != "y":
            self.rejected += 1
            self.say("  ✗ 已拒绝", "\033[31m")
            return ("<returncode>-1</returncode>\n<output>\n"
                    "用户拒绝执行这次调用。请换一个方案，或先解释你为什么要这么做。\n"
                    "</output>")

        return super().call_tool(tool_name, args)


# ==================================================================
if __name__ == "__main__":
    import os
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="v3confirm_")
    with open(os.path.join(tmpdir, "demo.py"), "w", encoding="utf-8") as f:
        f.write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")

    print("=" * 66)
    print("=== 白名单判断（只对 bash 生效）===")
    print("=" * 66)
    a = build_agent(mock=True, cwd=tmpdir, agent_class=ConfirmAgent)
    for c in ["ls -la", "nl -ba demo.py", "git status",
              "rm -f x", "cat > f.py", "pip install requests"]:
        print(f"  {'✓ 放行' if a.is_safe(c) else '⚠ 要确认'}   {c}")
    print("\n  edit_file 【永远要确认】—— 它总是在改文件")

    print()
    print("=" * 66)
    print("=== 完整流程（假answer：y, n, y, y, y）===")
    print("=" * 66)
    answer = iter(["y"] * 20)

    def fake_ask(prompt):
        a = next(answer)
        print(prompt + f"\033[36m{a}\033[0m")
        return a

    agent = build_agent(mock=True, cwd=tmpdir, agent_class=ConfirmAgent)
    agent.ask = fake_ask
    agent.whitelist = []          # 清空白名单，让每次都要确认
    agent.run("给 demo.py 的 div 加除零检查")
    print(f"\n  被拒绝了 {agent.rejected} 次")
    print("\n  最终文件内容：")
    print("  " + open(os.path.join(tmpdir, "demo.py"), encoding="utf-8").read().replace("\n", "\n  "))
