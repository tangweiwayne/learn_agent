"""
v3 · Agent：改用工具调用

和 v2 的差别只有 step() 一个方法：
  v2:  reply(字符串) → 正则抠命令 → 执行 → 结果拼成字符串塞回 user 消息
  v3:  message(字典) → 直接读 tool_calls → 执行 → 结果放进 role="tool" 消息

parse_action() 和那个正则，整个删掉了。
"""

import json
import os
import platform
import re

from v3_env import LocalEnvironment
from v3_model import BudgetExceeded, DeepSeekModel, MockModel

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------- 迷你模板引擎（和 v2 一样，没改）----------
def render(template: str, **variables) -> str:
    def _handle_if(m):
        return m.group(2) if variables.get(m.group(1)) else ""

    out = re.sub(r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}",
                 _handle_if, template, flags=re.DOTALL)

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


class Agent:
    def __init__(self, model, env, *, system_template, instance_template,
                 step_limit=20, done_marker="TASK_DONE", verbose=True):
        self.model = model
        self.env = env
        self.system_template = system_template
        self.instance_template = instance_template
        self.step_limit = step_limit
        self.done_marker = done_marker
        self.verbose = verbose
        self.messages = []
        self.step_count = 0

    def template_vars(self, **extra) -> dict:
        u = platform.uname()
        base = {
            "system": u.system, "machine": u.machine, "cwd": self.env.cwd,
            "done_marker": self.done_marker,
            "is_mac": u.system == "Darwin", "is_linux": u.system == "Linux",
        }
        base.update(extra)
        return base

    def say(self, text, color=""):
        if self.verbose:
            print(f"{color}{text}\033[0m" if color else text)

    # ---------------- 主循环（和 v2 一样）----------------
    def run(self, task: str) -> list:
        v = self.template_vars(task=task)
        self.messages = [
            {"role": "system", "content": render(self.system_template, **v)},
            {"role": "user", "content": render(self.instance_template, **v)},
        ]
        for _ in range(self.step_limit):
            self.step_count += 1
            try:
                if self.step():
                    return self.messages
            except BudgetExceeded as e:
                self.say(f"\n⛔ {e}", "\033[31m")
                return self.messages
        self.say(f"\n⚠️ 达到步数上限（{self.step_limit} 步），强制停止", "\033[33m")
        return self.messages

    # ---------------- 一步：这是 v3 唯一真正改动的地方 ----------------
    def step(self) -> bool:
        message = self.query()
        tool_calls = message.get("tool_calls") or []

        # 情况 A：模型只说话，没调用工具 → 提醒它，下一轮重来
        if not tool_calls:
            self.messages.append({
                "role": "user",
                "content": "你这一轮没有调用任何工具。请调用 bash 工具执行一条命令；"
                           f"如果任务已完成，就执行 `echo {self.done_marker}`。",
            })
            self.say("  ⚠ 这一轮没有工具调用，已提醒模型", "\033[33m")
            return False

        # 情况 B：正常，逐个执行
        finished = False
        for tc in tool_calls:
            command = self.取出命令(tc)
            observation = self.execute_action(command)
            # 结果用 role="tool" 回传，并带上 tool_call_id 做配对
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": observation,
            })
            self.say(f"----- 执行结果 -----\n{observation}", "\033[32m")
            if command.strip() == f"echo {self.done_marker}":
                finished = True

        if finished:
            self.say("\n✅ 任务结束  " + self.model.stats(), "\033[36m")
        return finished

    def 取出命令(self, tool_call: dict) -> str:
        """从一个 tool_call 里拿出 command。比正则简单太多。"""
        try:
            args = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            return "echo '参数不是合法 JSON'"
        return args.get("command", "")

    def query(self) -> dict:
        message = self.model.query(self.messages)
        self.messages.append(message)
        思考 = message.get("content") or "(没有文字说明)"
        self.say(
            f"\n===== 第 {self.step_count} 步 · 模型说 "
            f"(累计 ${self.model.total_cost:.4f}) =====\n{思考}",
            "\033[31m",
        )
        for tc in message.get("tool_calls") or []:
            self.say(f"  🔧 {tc['function']['name']}: {self.取出命令(tc)}", "\033[35m")
        return message

    def execute_action(self, command: str) -> str:
        return self.env.execute(command)


def build_agent(*, mock=True, cwd=None, agent_class=Agent, **overrides):
    cfg = load_config()
    cfg.update(overrides)
    env = LocalEnvironment(cwd=cwd, timeout=cfg["timeout"],
                           max_output_chars=cfg["max_output_chars"])
    model = MockModel() if mock else DeepSeekModel(cost_limit=cfg["cost_limit"])
    return agent_class(model, env,
                       system_template=load_prompt("system.txt"),
                       instance_template=load_prompt("instance.txt"),
                       step_limit=cfg["step_limit"],
                       done_marker=cfg["done_marker"])


if __name__ == "__main__":
    agent = build_agent(mock=True, cwd="/tmp")
    agent.run("统计 /tmp 下有多少个 .py 文件")
    print("\n" + "=" * 62)
    print(f"步数 {agent.step_count} | {agent.model.stats()} | 消息 {len(agent.messages)} 条")
    print("\n消息角色序列：")
    for i, m in enumerate(agent.messages):
        标记 = ""
        if m.get("tool_calls"):
            标记 = "  🔧 带 tool_calls"
        if m.get("tool_call_id"):
            标记 = f"  ↩ 回应 {m['tool_call_id']}"
        print(f"   [{i}] {m['role']:10s}{标记}")
