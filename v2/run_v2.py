"""v2 的入口。

用法：
    python3 run_v2.py "你的任务"              # 真模型 + 逐条确认（推荐）
    python3 run_v2.py "你的任务" --yolo        # 真模型 + 不确认
    python3 run_v2.py "你的任务" --mock        # 假模型，不花钱
"""

import os
import sys

from v2_agent import Agent, build_agent
from v2_confirm import ConfirmAgent
from v2_model import BudgetExceeded

if __name__ == "__main__":
    args = sys.argv[1:]
    mock = "--mock" in args
    yolo = "--yolo" in args
    任务 = next((a for a in args if not a.startswith("--")), None)
    if not 任务:
        任务 = input("任务：")

    agent = build_agent(
        mock=mock,
        cwd=os.getcwd(),                                  # 在你当前所在目录干活
        agent_class=Agent if yolo else ConfirmAgent,      # 默认带确认
    )

    print(f"\n模式: {'mock' if mock else 'DeepSeek'} / {'yolo' if yolo else 'confirm'}")
    print(f"目录: {agent.env.cwd}")
    print(f"上限: {agent.step_limit} 步, ${agent.model.cost_limit}\n")

    try:
        agent.run(任务)
    except BudgetExceeded as e:
        print(f"\n⛔ {e}")
    except KeyboardInterrupt:
        print("\n\n已中断")

    print(f"\n{'='*50}")
    print(f"步数 {agent.step_count} | {agent.model.stats()} | 消息 {len(agent.messages)} 条")
    if isinstance(agent, ConfirmAgent):
        print(f"你拒绝了 {agent.rejected} 条命令")
