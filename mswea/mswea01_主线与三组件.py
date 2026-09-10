"""mini-swe-agent 第一讲：只看主线和三个核心组件。

这是一个教学缩小版，不导入官方包、不联网、不调用真实模型。
它刻意保留官方代码最重要的数据形状和调用顺序：

    Agent.run
        -> Model.query
        -> Environment.execute
        -> Model.format_observation_messages
        -> 下一轮

运行：
    cd ~/Documents/learn_agent
    python3 mswea/mswea01_主线与三组件.py
"""

from __future__ import annotations

import subprocess


DONE_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"


class Submitted(Exception):
    """不是故障，而是“任务正常结束，并携带 exit 消息”的信号。"""

    def __init__(self, message: dict):
        self.message = message
        super().__init__()


def assistant_message(thought: str, command: str, call_id: str) -> dict:
    """制造一条接近 OpenAI tool-call 格式的假模型消息。"""
    return {
        "role": "assistant",
        "content": thought,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "bash",
                    "arguments": {"command": command},
                },
            }
        ],
        # 官方 Model 已经把 tool_calls 解析成 Agent 统一认识的 actions。
        "extra": {
            "actions": [
                {
                    "command": command,
                    "tool_call_id": call_id,
                }
            ],
            "cost": 0.0,
        },
    }


class FakeModel:
    """代替真实 LitellmModel：不联网，只按顺序念两句台词。"""

    def __init__(self):
        self.outputs = [
            assistant_message(
                "第一步：让 Environment 执行一条普通命令。",
                "printf 'hello from environment\\n'",
                "call_1",
            ),
            assistant_message(
                "第二步：输出结束标记和最终答案。",
                f"printf '{DONE_MARKER}\\n演示完成\\n'",
                "call_2",
            ),
        ]
        self.index = 0

    def query(self, messages: list[dict]) -> dict:
        print(f"\n[Model.query] 收到 {len(messages)} 条历史消息")
        message = self.outputs[self.index]
        self.index += 1
        command = message["extra"]["actions"][0]["command"]
        print(f"[Model.query] 决定下一条 action: {command!r}")
        return message

    def format_message(self, **kwargs) -> dict:
        """官方允许不同 Model 决定 system/user 消息长什么样。"""
        return kwargs

    def format_observation_messages(
        self,
        message: dict,
        outputs: list[dict],
        template_vars: dict | None = None,
    ) -> list[dict]:
        """把 Environment 的原始字典，变成下一轮发给模型的 tool 消息。"""
        actions = message["extra"]["actions"]
        observations = []
        for action, output in zip(actions, outputs):
            observations.append(
                {
                    "role": "tool",
                    "tool_call_id": action["tool_call_id"],
                    "content": (
                        f"<returncode>{output['returncode']}</returncode>\n"
                        f"<output>\n{output['output']}</output>"
                    ),
                }
            )
        return observations


class FakeLocalEnvironment:
    """缩小版 LocalEnvironment：执行 bash，返回原始结果字典。"""

    def execute(self, action: dict) -> dict:
        command = action.get("command", "")
        print(f"[Environment.execute] 正在执行: {command!r}")
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=5,
        )
        output = {
            "output": result.stdout + result.stderr,
            "returncode": result.returncode,
            "exception_info": "",
        }

        lines = output["output"].lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == DONE_MARKER and output["returncode"] == 0:
            submission = "".join(lines[1:])
            raise Submitted(
                {
                    "role": "exit",
                    "content": submission,
                    "extra": {
                        "exit_status": "Submitted",
                        "submission": submission,
                    },
                }
            )

        print(f"[Environment.execute] 原始结果: {output!r}")
        return output


class MiniAgent:
    """缩小版 DefaultAgent：只负责循环、消息历史和组件调度。"""

    def __init__(self, model, env):
        self.model = model
        self.env = env
        self.messages = []

    def add_messages(self, *messages: dict) -> list[dict]:
        self.messages.extend(messages)
        return list(messages)

    def run(self, task: str) -> dict:
        self.messages = [
            self.model.format_message(role="system", content="你是 coding agent。"),
            self.model.format_message(role="user", content=task),
        ]

        while True:
            try:
                self.step()
            except Submitted as submitted:
                self.add_messages(submitted.message)

            if self.messages[-1]["role"] == "exit":
                return self.messages[-1]["extra"]

    def step(self) -> list[dict]:
        # 官方写成一行：return self.execute_actions(self.query())
        message = self.query()
        observations = self.execute_actions(message)
        return observations

    def query(self) -> dict:
        message = self.model.query(self.messages)
        self.add_messages(message)
        return message

    def execute_actions(self, message: dict) -> list[dict]:
        actions = message.get("extra", {}).get("actions", [])
        outputs = [self.env.execute(action) for action in actions]
        observations = self.model.format_observation_messages(message, outputs)
        return self.add_messages(*observations)


def print_history(messages: list[dict]) -> None:
    print("\n最终 messages：")
    for index, message in enumerate(messages):
        role = message["role"]
        content = str(message.get("content", "")).strip()
        print(f"  [{index}] {role:<9} {content!r}")


if __name__ == "__main__":
    agent = MiniAgent(FakeModel(), FakeLocalEnvironment())
    result = agent.run("演示一次 mini-swe-agent 的主循环")
    print_history(agent.messages)

    # 两个小断言就是最小测试：不满足预期时，程序会在这里报错。
    assert result == {"exit_status": "Submitted", "submission": "演示完成\n"}
    assert [message["role"] for message in agent.messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "exit",
    ]
    print("\n✅ 主线与消息顺序都符合预期")
