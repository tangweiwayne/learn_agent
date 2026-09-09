"""
v3 · Agent：改用工具call

和 v2 的差别只有 step() 一个方法：
  v2:  reply(字符串) → 正则抠命令 → 执行 → 结果拼成字符串塞回 user 消息
  v3:  message(字典) → 直接读 tool_calls → 执行 → 结果放进 role="tool" 消息

parse_action() 和那个正则，整个删掉了。
"""

import datetime
import json
import os
import platform
import re

from v3_env import LocalEnvironment
from v3_model import BudgetExceeded, DeepSeekModel, MockModel
from v3_tools import edit_file

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
                 step_limit=20, done_marker="TASK_DONE", verbose=True,
                 reflect_before_done=True):
        self.model = model
        self.env = env
        self.system_template = system_template
        self.instance_template = instance_template
        self.step_limit = step_limit
        self.done_marker = done_marker
        self.verbose = verbose
        self.reflect_before_done = reflect_before_done
        self.messages = []
        self.step_count = 0
        self.has_reflected = False      # 自检只做一次
        self.task = ""                  # 记住原始任务，自检时要用

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
        self.task = task
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

        # 情况 A：模型只说话，没有调用工具 → 提醒它，下一轮重来
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
            tool_name = tc["function"]["name"]
            args = self.parse_args(tc)
            observation = self.call_tool(tool_name, args)
            # 结果用 role="tool" 回传，并带上 tool_call_id 做配对
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": observation,
            })
            self.say(f"----- 执行结果 -----\n{observation}", "\033[32m")
            if self.is_done_signal(observation):
                if self.reflect_before_done and not self.has_reflected:
                    self.has_reflected = True          # 只插这一次
                    self.messages.append({
                        "role": "user",
                        "content": render(load_prompt("reflect.txt"),
                                          **self.template_vars(task=self.task)),
                    })
                    self.say("\n🔍 完成前自检 —— 对照任务逐条核对", "\033[36m")
                    return False                        # 这一轮先不结束
                finished = True

        if finished:
            self.say("\n✅ 任务结束  " + self.model.stats(), "\033[36m")
        return finished

    def is_done_signal(self, observation: str) -> bool:
        """看【命令输出里】有没有暗号，而不是比对命令文本本身。

        为什么改：模型写 `cd /path && echo TASK_DONE` 时，
        命令文本对不上，但输出里是有 TASK_DONE 的。
        """
        for line in observation.splitlines():
            if line.strip() == self.done_marker:
                return True
        return False

    def parse_args(self, tool_call: dict) -> dict:
        """从一个 tool_call 里拿出args字典。"""
        try:
            return json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            return {}

    # ---------- 分派：模型说调哪个工具，就走哪条路 ----------
    def call_tool(self, tool_name: str, args: dict) -> str:
        """子类重写这个方法就能加闸门（比如人工确认）。"""
        if tool_name == "bash":
            return self.execute_action(args.get("command", ""))
        if tool_name == "edit_file":
            return edit_file(
                args.get("path", ""), args.get("old", ""), args.get("new", ""),
                cwd=self.env.cwd,
            )
        return f"<error>没有叫 {tool_name} 的工具</error>"

    def query(self) -> dict:
        message = self.model.query(self.messages)
        self.messages.append(message)
        thought = message.get("content") or "(没有文字说明)"
        self.say(
            f"\n===== 第 {self.step_count} 步 · 模型说 "
            f"(累计 ${self.model.total_cost:.4f}) =====\n{thought}",
            "\033[31m",
        )
        for tc in message.get("tool_calls") or []:
            name_ = tc["function"]["name"]
            args = self.parse_args(tc)
            if name_ == "bash":
                summary = args.get("command", "")
            elif name_ == "edit_file":
                old_s = args.get("old", "").replace("\n", "⏎")[:30]
                new_s = args.get("new", "").replace("\n", "⏎")[:30]
                summary = f"{args.get('path')}   {old_s!r} → {new_s!r}"
            else:
                summary = str(args)[:60]
            self.say(f"  🔧 {name_}: {summary}", "\033[35m")
        return message

    def execute_action(self, command: str) -> str:
        return self.env.execute(command)

    # ---------------- 轨迹保存 ----------------
    def serialize(self) -> dict:
        """把 agent 的全部状态组装成一个 json 能存的字典。

        只做组装，不碰文件 —— 这样想换存储方式只要改 save_trace()。
        """
        return {
            "task": self.task,
            "info": {
                "agent_class": type(self).__name__,
                "steps": self.step_count,
                "n_calls": self.model.n_calls,
                "cost": round(self.model.total_cost, 6),
                "model": getattr(self.model, "model_name", "mock"),
                "tools": [t["function"]["name"] for t in self.model.tools],
                "cwd": self.env.cwd,
                "step_limit": self.step_limit,
                "reflected": self.has_reflected,
                "n_messages": len(self.messages),
                "finished": bool(self.messages) and any(
                    self.is_done_signal(m.get("content") or "")
                    for m in self.messages if m.get("role") == "tool"
                ),
                "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            },
            "messages": self.messages,
        }

    def save_trace(self, path: str = "") -> str:
        """把轨迹写成 json 文件，返回文件路径。"""
        if not path:
            os.makedirs(os.path.join(HERE, "traces"), exist_ok=True)
            戳 = datetime.datetime.now().strftime("%m%d_%H%M%S")
            path = os.path.join(HERE, "traces", f"{戳}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.serialize(), f, ensure_ascii=False, indent=2)
        return path


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
    # 造一个干净的tmpdir，免得 mock 演示在 /tmp 里列出一堆系统垃圾
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="v3demo_")
    with open(os.path.join(tmpdir, "demo.py"), "w", encoding="utf-8") as f:
        f.write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")
    agent = build_agent(mock=True, cwd=tmpdir)
    print(f"演示tmpdir: {tmpdir}\n")
    agent.run("给 demo.py 的 div 加上除零检查")
    print("\n" + "=" * 62)
    print(f"步数 {agent.step_count} | {agent.model.stats()} | 消息 {len(agent.messages)} 条")
    print("\n消息角色序列：")
    for i, m in enumerate(agent.messages):
        mark = ""
        if m.get("tool_calls"):
            mark = "  🔧 带 tool_calls"
        if m.get("tool_call_id"):
            mark = f"  ↩ 回应 {m['tool_call_id']}"
        print(f"   [{i}] {m['role']:10s}{mark}")
