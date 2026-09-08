"""
第三课 · 第一个类：LocalEnvironment

把第一课的 execute() 函数，改造成一个"带配置的对象"。
解决两个问题：
  1. 配置（超时、目录、输出上限）存在实例身上，不用每次传参
  2. 加了输出截断 —— 这是我们从真实运行里发现的问题
"""

import os
import subprocess


class LocalEnvironment:
    """在本机执行 bash 命令。"""

    def __init__(self, cwd=None, timeout=30, max_output_chars=10000):
        # __init__ 在 LocalEnvironment(...) 的瞬间自动执行
        # self.xxx = ... 就是"把数据挂到这个实例身上"
        self.cwd = cwd or os.getcwd()      # or：cwd 是 None 就用当前目录
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    def execute(self, command: str) -> str:
        """执行一条命令，返回给模型看的格式化文本。"""
        try:
            r = subprocess.run(
                command,
                shell=True,
                text=True,
                capture_output=True,
                timeout=self.timeout,       # ← 从 self 拿，不用传参
                cwd=self.cwd,               # ← 从 self 拿
            )
            returncode = r.returncode
            output = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            returncode = -1
            output = f"命令超时（{self.timeout} 秒）"

        output = self._truncate(output)
        return f"<returncode>{returncode}</returncode>\n<output>\n{output}</output>"

    def _truncate(self, text: str) -> str:
        """输出太长就只保留头尾。下划线开头 = 内部方法，外面别调。"""
        if len(text) <= self.max_output_chars:
            return text
        half = self.max_output_chars // 2
        omitted = len(text) - 2 * half
        return (
            text[:half]
            + f"\n\n…（中间省略了 {omitted} 个字符，"
            + "如需查看请用 head / tail / grep 缩小范围）…\n\n"
            + text[-half:]
        )


# ------------------------------------------------------------------
if __name__ == "__main__":
    print("=== 1. 默认配置 ===")
    env = LocalEnvironment()
    print("self.cwd =", env.cwd)
    print("self.timeout =", env.timeout)
    print(env.execute("echo 你好"))

    print("\n=== 2. 命令失败 ===")
    print(env.execute("cat 不存在的文件"))

    print("\n=== 3. 自定义配置：换目录 + 缩短超时 ===")
    env2 = LocalEnvironment(cwd="/tmp", timeout=2)
    print(env2.execute("pwd"))
    print(env2.execute("sleep 5"))

    print("\n=== 4. 两个实例互不干扰 ===")
    print(f"env.cwd  = {env.cwd}")
    print(f"env2.cwd = {env2.cwd}")

    print("\n=== 5. 输出截断（故意把上限设成 200）===")
    env3 = LocalEnvironment(max_output_chars=200)
    print(env3.execute("seq 1 500"))
