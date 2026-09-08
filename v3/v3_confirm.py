"""
v3 · ConfirmAgent（和 v2 一样，只是 import 换了）

继承 Agent，只重写 execute_action 这一个方法，
就给 agent 装上了"每条危险命令先问你 y/n"的闸门。
run() / step() / query() / parse_action() 一个字都没改。
"""

import re

from v3_agent import Agent, build_agent

# 白名单：每条只描述"一段"命令（不含 && | 组合），全是只读操作
SAFE_PATTERNS = [
    r"^ls(\s|$)", r"^pwd$", r"^cd\s+\S+$",
    r"^cat\s+\S+$", r"^head\s", r"^tail\s", r"^nl\s", r"^wc(\s|$)",
    r"^grep\s", r"^find\s", r"^which\s", r"^echo\s+\S+$",
    r"^git\s+(status|diff|log|branch)(\s|$)",
    r"^python3?\s+--version$",
]

# 出现这些符号，说明命令可能在写文件或嵌套执行别的命令，一律不放行
DANGER_SIGNS = [">", ";", "`", "$("]


class ConfirmAgent(Agent):
    def __init__(self, *args, mode="confirm", whitelist=None, ask=input, **kwargs):
        # *args / **kwargs：自己不认识的参数，原样转给父类
        super().__init__(*args, **kwargs)
        self.mode = mode                  # confirm=每条危险的都问 / yolo=全放行
        self.whitelist = SAFE_PATTERNS if whitelist is None else whitelist
        self.ask = ask                    # 依赖注入：测试时可以换成假的
        self.rejected = 0

    def is_safe(self, command: str) -> bool:
        """四道关，全过才算安全。"""
        # ① 多行命令（heredoc 等）一律要确认
        if "\n" in command:
            return False
        # ② 含有重定向 / 命令分隔 / 命令替换符号 → 一律要确认
        if any(s in command for s in DANGER_SIGNS):
            return False
        # ③ 按 && || | 拆成若干段
        段落 = [s.strip() for s in re.split(r"&&|\|\||\|", command) if s.strip()]
        # ④ 每一段都必须在白名单里（all = 全都要真）
        return bool(段落) and all(
            any(re.search(p, seg) for p in self.whitelist) for seg in 段落
        )

    # ▼▼▼ 全部的改动就是重写这一个方法 ▼▼▼
    def execute_action(self, command: str) -> str:
        if self.mode == "yolo":
            return super().execute_action(command)

        if self.is_safe(command):
            self.say(f"  ✓ 白名单放行: {command}", "\033[90m")
            return super().execute_action(command)

        答案 = self.ask(
            f"\n\033[43m\033[30m 需要确认 \033[0m 即将执行：\n"
            f"    \033[1m{command}\033[0m\n"
            f"  [y]执行  [n]拒绝  [a]以后都别问  > "
        ).strip().lower()

        if 答案 == "a":
            self.mode = "yolo"
            self.say("  → 切换到 yolo 模式，后面不再询问", "\033[33m")
            return super().execute_action(command)

        if 答案 != "y":
            self.rejected += 1
            self.say("  ✗ 已拒绝", "\033[31m")
            # 关键：拒绝的理由要变成一条"观察结果"喂回给模型，让它换个做法
            return ("<returncode>-1</returncode>\n<output>\n"
                    "用户拒绝执行这条命令。请换一个方案，或先解释你为什么要这么做。\n"
                    "</output>")

        return super().execute_action(command)


# ==================================================================
if __name__ == "__main__":
    print("=" * 68)
    print("=== 1. 白名单判断 ===")
    a = ConfirmAgent(*[], **{}, model=None, env=None,
                     system_template="", instance_template="") \
        if False else None   # 占位，下面用 build_agent 造

    agent = build_agent(mock=True, cwd="/tmp", agent_class=ConfirmAgent)
    测试命令 = [
        "ls -la",
        "cat config.py",
        "git status",
        "rm -rf /tmp/x",
        "sed -i 's/a/b/' main.py",
        "pip install requests",
        "cat > f.py << 'EOF'\nprint(1)\nEOF",
    ]
    for c in 测试命令:
        单行 = c.replace("\n", "\\n")
        print(f"  {'✓ 白名单，直接执行' if agent.is_safe(c) else '⚠ 危险，需要确认'}   {单行[:42]}")

    print()
    print("=" * 68)
    print("=== 2. 用假的 ask 演示完整流程（真实使用时是 input）===")
    print("    假设用户依次回答：y, n, y, y")
    print()

    预设答案 = iter(["y", "n", "y", "y"])

    def 假的ask(提示):
        答 = next(预设答案)
        print(提示 + f"\033[36m{答}\033[0m")     # 把"用户输入"也打出来
        return 答

    agent2 = build_agent(mock=True, cwd="/tmp", agent_class=ConfirmAgent)
    agent2.ask = 假的ask
    agent2.whitelist = []          # 故意清空白名单，让每条都要确认
    agent2.run("统计 /tmp 下有多少个 .py 文件")
    print(f"\n  被拒绝了 {agent2.rejected} 条命令")

    print()
    print("=" * 68)
    print("=== 3. yolo 模式：全放行，一次都不问 ===")
    agent3 = build_agent(mock=True, cwd="/tmp", agent_class=ConfirmAgent)
    agent3.mode = "yolo"
    agent3.verbose = False
    agent3.run("统计 .py 文件")
    print(f"  跑完了，问了 0 次。步数={agent3.step_count}  被拒={agent3.rejected}")

    print()
    print("=" * 68)
    print("=== 4. 证明：ConfirmAgent 自己只写了 4 个方法，其余全继承 ===")
    自己的 = [k for k in ConfirmAgent.__dict__ if not k.startswith("__")]
    继承的 = [k for k in Agent.__dict__ if not k.startswith("__") and k not in 自己的]
    print(f"  自己写的: {自己的}")
    print(f"  白拿的  : {继承的}")
