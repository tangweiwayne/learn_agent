"""跑一遍全部 eval 任务，出一张成绩表。

用法：
    python3 run_eval.py --selftest   # 先检查"我的 check 写得对不对"（不花钱）
    python3 run_eval.py --mock       # 用假模型跑通管道（不花钱，预期全 fail）
    python3 run_eval.py              # 真跑，大约 $0.05
    python3 run_eval.py fix_bug      # 只跑一个任务
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))          # 为了 import v3_agent

from tasks import TASKS
from v3_agent import Agent, build_agent


# ================================================================
def selftest():
    """检查每个 check 是不是【真的在判事】。

    做法：铺完靶场，一步都不跑，直接 check。
    这时候必须 False —— 如果返回 True，说明这个 check 不做任何事就能通过，
    那它永远不会失败，写了等于没写。
    """
    print("自测：靶场刚铺好、agent 一步没跑时，每个 check 都必须判 False\n")
    ok_all = True
    for t in TASKS:
        d = tempfile.mkdtemp(prefix=f"selftest_{t['id']}_")
        try:
            state = t["setup"](d)

            class 空Agent:          # 假装跑过，但什么都没做
                messages = []
                step_count = 0

            ok, why = t["check"](d, 空Agent(), state)
            good = not ok
            ok_all &= good
            print(f"  {'✅' if good else '❌'} {t['id']:<16} "
                  f"check 返回 {ok}  ——  {why}")
            if ok:
                print(f"     ⚠️ 这个 check 白手起家就能过，它判不出任何东西！")
        finally:
            shutil.rmtree(d, ignore_errors=True)
    print("\n" + ("✅ 三个 check 都有判别力" if ok_all else "❌ 有 check 是摆设"))
    return ok_all


# ================================================================
def run_one(task: dict, mock: bool, outdir: str) -> dict:
    workdir = tempfile.mkdtemp(prefix=f"eval_{task['id']}_")
    state = task["setup"](workdir)
    agent = build_agent(mock=mock, cwd=workdir, agent_class=Agent,
                        step_limit=task.get("step_limit", 15))
    agent.verbose = False                      # eval 不要刷屏

    error = ""
    try:
        agent.run(task["prompt"])
    except Exception as e:                     # 崩了也算一种结果，别让整场 eval 挂掉
        error = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    try:
        ok, why = task["check"](workdir, agent, state)
    except Exception as e:
        ok, why = False, f"check 自己炸了：{type(e).__name__}: {e}"

    # ★ 用任务名当文件名，不用时间戳 —— 同一秒跑完两个任务会互相覆盖
    trace = agent.save_trace(os.path.join(outdir, f"{task['id']}.json"))
    shutil.rmtree(workdir, ignore_errors=True)
    return {
        "id": task["id"],
        "ok": ok,
        "why": why,
        "steps": agent.step_count,
        "cost": round(agent.model.total_cost, 4),
        "error": error,
        "trace": os.path.relpath(trace, HERE),
    }


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(0 if selftest() else 1)

    mock = "--mock" in args
    only = [a for a in args if not a.startswith("--")]
    tasks = [t for t in TASKS if not only or t["id"] in only]

    stamp = datetime.datetime.now().strftime("%m%d_%H%M%S")
    outdir = os.path.join(HERE, "results", stamp)
    os.makedirs(outdir, exist_ok=True)

    print(f"\n跑 {len(tasks)} 个任务，模式：{'mock（预期全 fail）' if mock else 'DeepSeek 真跑'}")
    print(f"产物目录：{outdir}\n")
    results = []
    for t in tasks:
        print(f"  ▶ {t['id']} …", end="", flush=True)
        r = run_one(t, mock, outdir)
        results.append(r)
        print(f" {'✅' if r['ok'] else '❌'}  {r['steps']} 步  ${r['cost']:.4f}")

    print("\n" + "=" * 76)
    print(f"{'任务':<16}{'结果':<6}{'步数':>5}{'花费':>10}   说明")
    print("-" * 76)
    for r in results:
        print(f"{r['id']:<16}{'PASS' if r['ok'] else 'FAIL':<6}"
              f"{r['steps']:>5}{r['cost']:>10.4f}   {r['why'][:38]}")
    print("-" * 76)
    passed = sum(1 for r in results if r["ok"])
    print(f"{'合计':<16}{f'{passed}/{len(results)}':<6}"
          f"{sum(r['steps'] for r in results):>5}"
          f"{sum(r['cost'] for r in results):>10.4f}")

    out = os.path.join(outdir, "summary.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"when": stamp, "mock": mock, "results": results},
                  f, ensure_ascii=False, indent=2)
    print(f"\n成绩已存：{out}")
    print(f"每个任务的完整 trace 在同一目录下，按任务名命名")


if __name__ == "__main__":
    main()
