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
from v3_tools import ALL_TOOLS, SUBAGENT_TOOLS, edit_file, normalize_plan, render_plan

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
                 reflect_before_done=True,
                 compact_keep_steps=3, compact_min_chars=800,
                 tools=None, subagent_step_limit=8):
        self.model = model
        self.env = env
        self.system_template = system_template
        self.instance_template = instance_template
        self.step_limit = step_limit
        self.done_marker = done_marker
        self.verbose = verbose
        self.reflect_before_done = reflect_before_done
        self.compact_keep_steps = compact_keep_steps   # 最近几步保持原样（0=不压缩）
        self.compact_min_chars = compact_min_chars     # 只压超过这么长的老结果
        self.tools = tools if tools is not None else ALL_TOOLS
        self.subagent_step_limit = subagent_step_limit  # 子助手最多跑几步
        self.subagent_depth = 0        # 0=主 agent，1=子助手（不许再往下派）
        self.subagent_traces = []      # 子助手跑完的完整历史，存进 trace 供事后看
        self.report = None             # 子助手调 report 工具交上来的结论
        self.ask_human = input         # 被打断时问谁（测试时可以换成假函数）
        self.interrupts = 0            # 被打断过几次，存进 trace
        self.messages = []
        self.step_count = 0
        self.has_reflected = False      # 自检只做一次
        self.task = ""                  # 记住原始任务，自检时要用
        self.plan = []                  # 计划的每一步（字符串列表）
        self.plan_done = 0              # 做完到第几步

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
            except KeyboardInterrupt:
                # 子助手不自己处理，往上抛给主 agent 统一问
                if self.subagent_depth >= 1:
                    raise
                if not self.handle_interrupt():
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
        if tool_name == "update_plan":
            return self.update_plan(args.get("steps") or [])
        if tool_name == "task":
            return self.run_subagent(args.get("prompt", ""))
        if tool_name == "report":
            self.report = {"summary": args.get("summary", ""),
                           "confident": args.get("confident", "partial")}
            # 返回值里带上暗号，is_done_signal 会看到它，这一步就是最后一步
            return f"<报告已收到>\n{self.done_marker}"
        if tool_name == "bash":
            return self.execute_action(args.get("command", ""))
        if tool_name == "edit_file":
            return edit_file(
                args.get("path", ""), args.get("old", ""), args.get("new", ""),
                cwd=self.env.cwd,
            )
        return f"<error>没有叫 {tool_name} 的工具</error>"

    # ---------- 被打断时 ----------
    def repair_history(self) -> int:
        """补上"有 tool_calls 却没有对应 tool 消息"的窟窿，返回补了几个。

        打断可能正好发生在【模型已经回话、工具还没执行完】的中间。
        这时 messages 里躺着一条带 tool_calls 的 assistant，却没有配套的
        tool 消息 —— 这种历史发给 API 会直接 400。
        """
        answered = {m.get("tool_call_id") for m in self.messages
                    if m.get("role") == "tool"}
        holes = [tc["id"] for m in self.messages
                 for tc in (m.get("tool_calls") or [])
                 if tc["id"] not in answered]
        for call_id in holes:
            self.messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": "<interrupted>用户中断了这次执行，"
                           "这个工具没有运行，你也没有拿到它的结果。</interrupted>",
            })
        return len(holes)

    def handle_interrupt(self) -> bool:
        """Ctrl-C 之后问用户怎么办。返回 True=继续跑，False=就此结束。"""
        self.interrupts += 1
        holes = self.repair_history()          # ★ 先补洞，再问
        self.say(f"\n\n⏸  已暂停"
                 + (f"（补上了 {holes} 条被中断的工具结果）" if holes else ""),
                 "\033[33m")
        try:
            answer = self.ask_human(
                "  [回车]继续  [q]结束  [其它文字]作为新指令插进去 > "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            answer = "q"                       # 暂停时再按一次 Ctrl-C = 退出

        if answer.lower() == "q":
            self.say("  → 结束", "\033[33m")
            return False
        if answer:
            self.messages.append({
                "role": "user",
                "content": f"【用户中途插话】{answer}\n"
                           f"请把这条指令和原任务放在一起考虑，从现在这一步开始调整做法。",
            })
            self.say(f"  → 已插入指令：{answer}", "\033[33m")
        else:
            self.say("  → 继续", "\033[33m")
        return True

    # ---------- 子助手 ----------
    def final_answer(self) -> str:
        """结论。优先用 report 工具交上来的，没有才退回去猜最后一句话。"""
        if self.report:
            tag = {"yes": "", "partial": "（助手自评：只查实了一部分）\n",
                   "no": "（助手自评：没查出来）\n"}.get(self.report["confident"], "")
            return tag + self.report["summary"]
        for m in reversed(self.messages):
            if m.get("role") == "assistant" and (m.get("content") or "").strip():
                return m["content"].strip()
        return "(助手什么都没说)"

    def subagent_kwargs(self) -> dict:
        """子类重写这个，把自己特有的构造参数也传给子助手。

        base Agent 没有特有参数，返回空字典。
        ConfirmAgent 要把 mode/whitelist/ask 传下去，否则子助手不受确认闸门管。
        """
        return {}

    def run_subagent(self, prompt: str) -> str:
        """派一个子助手跑完整个 ReAct 循环，只把它的结论作为 observation 返回。

        输入：prompt —— 一段自包含的任务描述
        输出：一个字符串，会被塞进主 agent 的 role="tool" 消息
        """
        if not prompt.strip():
            return "<error>task 工具需要 prompt 参数，不能为空</error>"
        if self.subagent_depth >= 1:
            return "<error>你已经是子助手了，不能再往下派子助手。请自己用 bash 查。</error>"

        sub = type(self)(                # ★ 和自己同一个类：闸门/确认逻辑一起继承
            self.model,                  # ★ 同一个 model：花费和调用次数自动累加
            self.env,                    # ★ 同一个 env：同一个工作目录
            system_template=load_prompt("subagent.txt"),
            instance_template="{{task}}",
            step_limit=self.subagent_step_limit,
            done_marker=self.done_marker,
            verbose=self.verbose,
            reflect_before_done=False,   # 子任务小，不用自检
            compact_keep_steps=self.compact_keep_steps,
            compact_min_chars=self.compact_min_chars,
            tools=SUBAGENT_TOOLS,        # ★ 只给 bash
            **self.subagent_kwargs(),    # ★ 子类特有的参数（比如 ConfirmAgent 的 ask）
        )
        sub.subagent_depth = self.subagent_depth + 1

        self.say(f"\n┌─ 派出子助手 ──────────────\n│ {prompt}", "\033[34m")
        sub.run(prompt)
        self.say("└─ 子助手结束 ──────────────", "\033[34m")

        self.subagent_traces.append(sub.serialize())
        answer = sub.final_answer()
        raw = sum(len(str(m.get("content") or "")) for m in sub.messages)
        warn = ""
        if not any(self.is_done_signal(m.get("content") or "")
                   for m in sub.messages if m.get("role") == "tool"):
            warn = "（注意：助手没跑完就到步数上限了，结论可能不完整）\n"
        return (f"<subagent_result>\n{warn}{answer}\n</subagent_result>\n"
                f"（子助手用了 {sub.step_count} 步、内部产生 {raw:,} 字符，"
                f"这些都没有进入你的对话）")

    def query(self) -> dict:
        sent = self.compact(self.messages)          # ← 发出去的是压缩版
        if len(str(sent)) < len(str(self.messages)):
            省 = len(str(self.messages)) - len(str(sent))
            self.say(f"  ✂ 历史压缩：本次少发约 {省:,} 字符", "\033[90m")
        # 流式：先把表头打出来，正文由 on_text 回调一段一段吐
        streaming = getattr(self.model, "stream", False) and self.verbose
        if streaming:
            self.say(f"\n===== 第 {self.step_count} 步 · 模型说 "
                     f"(累计 ${self.model.total_cost:.4f}) =====", "\033[31m")
            self.model.on_text = lambda piece: print(
                f"\033[31m{piece}\033[0m", end="", flush=True)

        message = self.model.query(sent, self.tools)   # self.messages 仍是完整的

        if streaming:
            self.model.on_text = None    # 用完摘掉，免得别处误触发
            print()                      # 流完补一个换行
        self.messages.append(message)
        thought = message.get("content") or "(没有文字说明)"
        if not streaming:                # 非流式才在这里一次性打印
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
            elif name_ == "update_plan":
                _p = normalize_plan(args.get("steps") or [])
                _d = sum(1 for it in _p if it["status"] == "done")
                summary = f"{len(_p)} 步，已完成 {_d}"
            elif name_ == "edit_file":
                old_s = args.get("old", "").replace("\n", "⏎")[:30]
                new_s = args.get("new", "").replace("\n", "⏎")[:30]
                summary = f"{args.get('path')}   {old_s!r} → {new_s!r}"
            else:
                summary = str(args)[:60]
            self.say(f"  🔧 {name_}: {summary}", "\033[35m")
        return message

    def update_plan(self, steps: list) -> str:
        """记住计划，返回渲染好的清单给模型看。

        这是唯一【有状态】的工具 —— bash 和 edit_file 执行完就没了，
        计划却要跨步骤存在，所以挂在 self 上。

        输入 steps 是模型填的，格式不保证 —— 先用 normalize_plan 规范化。
        """
        self.plan = normalize_plan(steps)
        self.plan_done = sum(1 for it in self.plan if it["status"] == "done")
        return render_plan(self.plan)

    def execute_action(self, command: str) -> str:
        return self.env.execute(command)

    # ---------------- 轨迹保存 ----------------
    def compact(self, messages: list) -> list:
        """把【老的、长的】工具结果换成一行占位，减小发出去的上下文。

        规则：
          · 最近 compact_keep_steps 步的内容，原样保留
          · 更早的 role="tool" 消息，content 超过 compact_min_chars 的换成占位
          · system / user / assistant 一律不动
          · 【只换 content，不删消息】—— 删了会破坏 tool_call_id 配对

        输入输出都是 messages 列表；不修改原列表，返回新的。
        """
        if self.compact_keep_steps <= 0:
            return messages

        # 找出所有 assistant 消息的下标 = 每一步的位置
        marks = [i for i, m in enumerate(messages) if m.get("role") == "assistant"]
        if len(marks) <= self.compact_keep_steps:
            return messages                       # 还没跑几步，不用压

        cut = marks[-self.compact_keep_steps]      # 这个下标往后的全部保留

        out = []
        for i, m in enumerate(messages):
            content = m.get("content") or ""
            if (i >= cut
                    or m.get("role") != "tool"
                    or len(content) <= self.compact_min_chars):
                out.append(m)
                continue
            out.append({**m, "content": (
                f"<omitted>早前一条命令的执行结果，已省略 {len(content)} 字符。"
                f"如果还需要这些内容，请重新执行相应命令。</omitted>")})
        return out

    def _sent_size(self, messages: list) -> int:
        """这批消息压缩之后有多大 —— 这才是真正发出去、真正计费的量。

        算法必须和 context_growth 里算 chars 的方式一致（content + 工具参数），
        否则两个数不可比。
        """
        total = 0
        for m in self.compact(messages):
            total += len(str(m.get("content") or ""))
            for tc in m.get("tool_calls") or []:
                total += len(tc["function"].get("arguments") or "")
        return total

    def context_growth(self) -> list:
        """算出每一步发出去的上下文有多大（字符数）。

        返回形如：[{"step":1,"n_messages":2,"chars":1800}, ...]
        用来看"线性历史"到底膨胀得多快。
        """
        out, step, chars, n = [], 0, 0, 0
        for m in self.messages:
            if m.get("role") == "assistant":
                step += 1
                out.append({"step": step, "n_messages": n,
                            "chars": chars,                              # 压缩前
                            "sent": self._sent_size(self.messages[:n])})  # 实际发出去的
            chars += len(str(m.get("content") or ""))
            for tc in m.get("tool_calls") or []:
                chars += len(tc["function"].get("arguments") or "")
            n += 1
        return out

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
                "context_growth": self.context_growth(),
                "interrupts": self.interrupts,
                "plan": self.plan,
                "plan_done": self.plan_done,
                "n_messages": len(self.messages),
                "finished": bool(self.messages) and any(
                    self.is_done_signal(m.get("content") or "")
                    for m in self.messages if m.get("role") == "tool"
                ),
                "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            },
            "messages": self.messages,
            "subagent_traces": self.subagent_traces,
        }

    def save_trace(self, path: str = "") -> str:
        """把轨迹写成 json 文件，返回文件路径。"""
        if not path:
            os.makedirs(os.path.join(HERE, "traces"), exist_ok=True)
            stamp = datetime.datetime.now().strftime("%m%d_%H%M%S")
            path = os.path.join(HERE, "traces", f"{stamp}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.serialize(), f, ensure_ascii=False, indent=2)
        return path


def build_agent(*, mock=True, cwd=None, agent_class=Agent, **overrides):
    cfg = load_config()
    cfg.update(overrides)
    env = LocalEnvironment(cwd=cwd, timeout=cfg["timeout"],
                           max_output_chars=cfg["max_output_chars"])
    model = (MockModel() if mock else
             DeepSeekModel(cost_limit=cfg["cost_limit"],
                           stream=cfg.get("stream", False)))
    return agent_class(model, env,
                       system_template=load_prompt("system.txt"),
                       instance_template=load_prompt("instance.txt"),
                       step_limit=cfg["step_limit"],
                       done_marker=cfg["done_marker"],
                       compact_keep_steps=cfg.get("compact_keep_steps", 3),
                       compact_min_chars=cfg.get("compact_min_chars", 800),
                       subagent_step_limit=cfg.get("subagent_step_limit", 8))


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
