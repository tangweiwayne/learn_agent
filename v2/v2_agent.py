"""
第三课 · 第三个类：Agent

把 Model 和 Environment 装起来（组合），跑主循环。
提示词不再写在代码里，改从 prompts/*.txt 读，并支持模板变量。
"""

import json
import os
import platform
import re

from v2_env import LocalEnvironment
from v2_model import BudgetExceeded, DeepSeekModel, MockModel

HERE = os.path.dirname(os.path.abspath(__file__))


# ==================================================================
# 迷你模板引擎（15 行，正好用上模块4 学的正则）
# ==================================================================
def render(template: str, **variables) -> str:
    """支持 {{变量}} 和 {% if 变量 %}...{% endif %} 两种语法。"""

    def _handle_if(m):
        name, body = m.group(1), m.group(2)     # group(1)=变量名, group(2)=中间内容
        return body if variables.get(name) else ""

    out = re.sub(
        r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}",
        _handle_if, template, flags=re.DOTALL,
    )

    def _handle_var(m):
        name = m.group(1)
        if name not in variables:
            raise KeyError(f"模板里用了 {{{{{name}}}}}，但没提供这个变量")
        return str(variables[name])

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _handle_var, out)


def load_config() -> dict:
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def load_prompt(name: str) -> str:
    with open(os.path.join(HERE, "prompts", name), encoding="utf-8") as f:
        return f.read()


# ==================================================================
# Agent
# ==================================================================
class Agent:
    def __init__(self, model, env, *, system_template, instance_template,
                 step_limit=20, done_marker="TASK_DONE", verbose=True):
        # 组合：把别的对象装进来（has-a），不是继承（is-a）
        self.model = model
        self.env = env
        # 配置
        self.system_template = system_template
        self.instance_template = instance_template
        self.step_limit = step_limit
        self.done_marker = done_marker
        self.verbose = verbose
        # 状态
        self.messages = []
        self.step_count = 0

    # ---------- 模板变量 ----------
    def template_vars(self, **extra) -> dict:
        uname = platform.uname()
        base = {
            "system": uname.system,
            "machine": uname.machine,
            "cwd": self.env.cwd,
            "done_marker": self.done_marker,
            "is_mac": uname.system == "Darwin",
            "is_linux": uname.system == "Linux",
        }
        base.update(extra)          # extra 里的值会覆盖 base
        return base

    # ---------- 打印 ----------
    def say(self, text, color=""):
        if self.verbose:
            print(f"{color}{text}\033[0m" if color else text)

    # ---------- 主循环 ----------
    def run(self, task: str) -> list:
        v = self.template_vars(task=task)
        self.messages = [
            {"role": "system", "content": render(self.system_template, **v)},
            {"role": "user", "content": render(self.instance_template, **v)},
        ]
        for _ in range(self.step_limit):
            self.step_count += 1
            try:
                finished = self.step()
            except BudgetExceeded as e:
                self.say(f"\n⛔ {e}", "\033[31m")
                return self.messages
            if finished:
                return self.messages
        self.say(f"\n⚠️ 达到步数上限（{self.step_limit} 步），强制停止", "\033[33m")
        return self.messages

    # ---------- 一步 ----------
    def step(self) -> bool:
        """走一步。返回 True 表示任务结束。"""
        reply = self.query()
        try:
            command = self.parse_action(reply)
        except ValueError as e:
            self.messages.append({"role": "user", "content": f"格式错误：{e}，请重发。"})
            self.say(f"[格式错误] {e}", "\033[33m")
            return False

        observation = self.execute_action(command)
        self.say(f"----- 执行结果 -----\n{observation}", "\033[32m")

        if command.strip() == f"echo {self.done_marker}":
            self.say("\n✅ 任务结束  " + self.model.stats(), "\033[36m")
            return True

        self.messages.append({"role": "user", "content": observation})
        return False

    # ---------- 拆开的四个小步骤，方便子类单独重写 ----------
    def query(self) -> str:
        reply = self.model.query(self.messages)
        self.messages.append({"role": "assistant", "content": reply})
        self.say(
            f"\n===== 第 {self.step_count} 步 · 模型说 "
            f"(累计 ${self.model.total_cost:.4f}) =====\n{reply}",
            "\033[31m",
        )
        return reply

    def parse_action(self, reply: str) -> str:
        blocks = re.findall(r"```bash\n(.*?)\n```", reply, re.DOTALL)
        if len(blocks) != 1:
            raise ValueError(f"需要恰好 1 个 bash 代码块，实际找到 {len(blocks)} 个")
        return blocks[0].strip()

    def execute_action(self, command: str) -> str:
        """执行命令。单独拆出来，是为了让子类能在这里插一道闸。"""
        return self.env.execute(command)


# ==================================================================
def build_agent(*, mock=True, cwd=None, agent_class=Agent, **overrides):
    """按配置文件造一个 agent。"""
    cfg = load_config()
    cfg.update(overrides)
    env = LocalEnvironment(
        cwd=cwd, timeout=cfg["timeout"], max_output_chars=cfg["max_output_chars"]
    )
    model = MockModel() if mock else DeepSeekModel(cost_limit=cfg["cost_limit"])
    return agent_class(
        model, env,
        system_template=load_prompt("system.txt"),
        instance_template=load_prompt("instance.txt"),
        step_limit=cfg["step_limit"],
        done_marker=cfg["done_marker"],
    )


if __name__ == "__main__":
    print("=" * 62)
    print("=== 1. 模板引擎单独测试 ===")
    tpl = "任务：{{task}}\n{% if is_mac %}你在 Mac 上，注意 sed -i ''{% endif %}{% if is_linux %}你在 Linux 上{% endif %}\n系统：{{system}}"
    print("--- 当 is_mac=True ---")
    print(render(tpl, task="修bug", is_mac=True, is_linux=False, system="Darwin"))
    print("--- 当 is_linux=True（同一个模板）---")
    print(render(tpl, task="修bug", is_mac=False, is_linux=True, system="Linux"))
    print("--- 少给一个变量会怎样 ---")
    try:
        render("你好 {{name}}")
    except KeyError as e:
        print("  ⛔ KeyError:", e)

    print("\n" + "=" * 62)
    print("=== 2. 渲染后的真实提示词（前 22 行）===")
    a = build_agent(mock=True)
    v = a.template_vars(task="修复 buggy.py")
    for i, line in enumerate(render(a.instance_template, **v).splitlines()[:22], 1):
        print(f"  {i:2d}| {line}")

    print("\n" + "=" * 62)
    print("=== 3. 跑一遍 mock ===")
    agent = build_agent(mock=True, cwd="/tmp")
    agent.run("统计 /tmp 下有多少个 .py 文件")
    print(f"\n最终：{len(agent.messages)} 条消息，{agent.step_count} 步，{agent.model.stats()}")
