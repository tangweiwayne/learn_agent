# 手写 AI Agent · 学习目录

从零手写一个 coding agent，然后对照官方 mini-swe-agent 源码。

---

## 目录结构

```
learn_agent/
├── .env                    API key（v1/ 和 v2/ 都会自动往上找到它）
│
├── v1/                     【第一课】7 个散函数，60 行的最小 agent
│   ├── v1_loop.py             主文件
│   └── show_messages.py       看 messages 列表怎么长大
│
├── v2/                     【第三课】重构成 3 个类 + 配置外置
│   ├── v2_env.py              LocalEnvironment  执行命令 + 输出截断
│   ├── v2_model.py            Model / DeepSeekModel / MockModel  调模型 + 算钱
│   ├── v2_agent.py            render() + Agent  模板引擎 + 主循环
│   ├── v2_confirm.py          ConfirmAgent  白名单 + 人工确认
│   ├── run_v2.py              ★ 入口
│   ├── config.json            数值配置（步数、预算、超时）
│   ├── prompts/
│   │   ├── system.txt         系统提示词
│   │   └── instance.txt       任务提示词（带 {{变量}} 和 {% if %}）
│   ├── show_prompt.py         看模板→变量→渲染的全过程
│   └── demo_confirm.py        演示确认闸门（假模型，不花钱）
│
├── mine/                   自己写的练习
├── sandbox/                试验田（让 agent 在这里折腾）
└── mini-swe-agent/         官方源码（git clone 来的）
```

---

## 常用命令

```bash
# ---------- 跑 agent ----------
cd ~/Documents/learn_agent/sandbox

python3 ../v2/run_v2.py "你的任务"           # DeepSeek + 逐条确认（默认，最安全）
python3 ../v2/run_v2.py "你的任务" --yolo    # DeepSeek + 不确认
python3 ../v2/run_v2.py "你的任务" --mock    # 假模型，不花钱

# ---------- 第一课版本 ----------
cd ~/Documents/learn_agent/v1
python3 v1_loop.py --mock                   # 离线演示
python3 show_messages.py                    # 看 messages 怎么长大

# ---------- 看内部机制 ----------
cd ~/Documents/learn_agent/v2
python3 show_prompt.py                      # 模板 → 变量 → 渲染 全过程
python3 demo_confirm.py                     # 确认闸门（会真的问你 y/n）
python3 v2_env.py                           # 各模块的自测
python3 v2_model.py
python3 v2_agent.py
python3 v2_confirm.py

# ---------- 改配置（不用碰代码）----------
# 编辑 v2/config.json          → 步数上限、预算、超时、输出截断长度
# 编辑 v2/prompts/*.txt        → 提示词
```

---

## 你写的 vs 官方源码

| 你的文件 | 官方对应 | 行数 | 状态 |
|---|---|---|---|
| `v2/run_v2.py` | `run/hello_world.py` | 42 | ✅ 已读 |
| `v2/v2_env.py` | `environments/local.py` | 92 | ⬜ 下一个 |
| `v2/v2_model.py` | `models/litellm_model.py` | 164 | ⬜ |
| `v2/v2_agent.py` | `agents/default.py` | 190 | ⬜ |
| `v2/v2_confirm.py` | `agents/interactive.py` | ~150 | ⬜ |
| `v2/prompts/` + `config.json` | `config/default.yaml` | 170 | ⬜ |

官方源码本地路径前缀：`~/Documents/learn_agent/mini-swe-agent/src/minisweagent/`
GitHub：<https://github.com/SWE-agent/mini-swe-agent/tree/main/src/minisweagent>

---

## 核心思想（三句话）

1. **agent = 一个 while 循环**：把 LLM 的回复当 bash 命令执行，结果贴回对话，再问一次。
2. **一次恰好一条命令** —— 这是 agent 和脚本的分界线（走一步、看一眼、再决定）。
3. **一切意外都翻译成对话** —— 格式错误、用户拒绝、命令失败，都变成一条"观察结果"喂回去，让模型自愈。
