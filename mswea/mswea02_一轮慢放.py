"""mini-swe-agent 第二讲：把一次 step() 慢放成三个暂停点。

运行：
    cd ~/Documents/learn_agent
    python3 mswea/mswea02_一轮慢放.py

这里只跑第一轮普通命令，不进入结束分支。
"""

from mswea01_主线与三组件 import FakeLocalEnvironment, FakeModel


def show_messages(title: str, messages: list) -> None:
    print(f"\n{'=' * 62}")
    print(title)
    print(f"消息数：{len(messages)}")
    print("角色：", " -> ".join(message["role"] for message in messages))


model = FakeModel()
env = FakeLocalEnvironment()
messages = [
    model.format_message(role="system", content="你是 coding agent。"),
    model.format_message(role="user", content="请演示一轮。"),
]

show_messages("暂停点 0：还没问模型", messages)

# 暂停点 1：Agent.query()
message = model.query(messages)
messages.append(message)
show_messages("暂停点 1：Model 回答已加入历史", messages)

# 暂停点 2：Agent.execute_actions() 的前半段
actions = message.get("extra", {}).get("actions", [])
outputs = [env.execute(action) for action in actions]
print("\n暂停点 2：Environment 返回的还是原始字典")
print("outputs =", outputs)

# 暂停点 3：Agent.execute_actions() 的后半段
observations = model.format_observation_messages(message, outputs)
messages.extend(observations)
show_messages("暂停点 3：原始结果已包装成 tool 消息", messages)
print("tool content =", messages[-1]["content"])

assert len(messages) == 4
assert [message["role"] for message in messages] == [
    "system",
    "user",
    "assistant",
    "tool",
]
print("\n✅ 一轮完成：2 条初始消息 + 1 条模型消息 + 1 条工具消息 = 4 条")
