"""v3 入口 —— 工具调用版。

用法（在 sandbox 里跑）：
    python3 ../v3/run_v3.py "你的任务"           # DeepSeek + 逐条确认
    python3 ../v3/run_v3.py "你的任务" --yolo    # 不确认
    python3 ../v3/run_v3.py "你的任务" --mock    # 假模型，不花钱
    python3 ../v3/run_v3.py "你的任务" --stream  # 边生成边打印
"""

import os
import sys

from v3_agent import Agent, build_agent
from v3_confirm import ConfirmAgent
from v3_model import BudgetExceeded

if __name__ == "__main__":
    args = sys.argv[1:]
    mock = "--mock" in args
    yolo = "--yolo" in args
    stream = "--stream" in args
    任务 = next((a for a in args if not a.startswith("--")), None) or input("任务：")

    agent = build_agent(mock=mock, cwd=os.getcwd(),
                        agent_class=Agent if yolo else ConfirmAgent,
                        stream=stream)

    print(f"\n[v3 工具调用版] 模式: {'mock' if mock else 'DeepSeek'} / "
          f"{'yolo' if yolo else 'confirm'} / {'stream' if stream else '一次性'}")
    print(f"目录: {agent.env.cwd}")
    print(f"上限: {agent.step_limit} 步, ${agent.model.cost_limit}")
    # 把工具清单打出来 —— 这样"工具没发过去"这类 bug 一眼就能看见
    print(f"工具: {[t['function']['name'] for t in agent.tools]}\n")

    try:
        agent.run(任务)
    except BudgetExceeded as e:
        print(f"\n⛔ {e}")
    except KeyboardInterrupt:
        print("\n\n已中断")

    trace = agent.save_trace()
    print(f"\n{'=' * 50}")
    print(f"步数 {agent.step_count} | {agent.model.stats()} | 消息 {len(agent.messages)} 条")
    print(f"轨迹已存：{trace}")
    if isinstance(agent, ConfirmAgent):
        print(f"你拒绝了 {agent.rejected} 条命令")
