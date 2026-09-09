"""v3_tools.edit_file 的完整单元测试。

所有测试都在临时目录中进行，通过 edit_file 的 cwd 参数指向临时目录，
因此不会污染真实源码目录。
"""

import os
import sys
import tempfile
import unittest

# 让模块可被 import
MODULE_DIR = os.path.expanduser("~/Documents/learn_agent/v3")
sys.path.insert(0, MODULE_DIR)

from v3_tools import edit_file


class EditFileTest(unittest.TestCase):
    def setUp(self):
        # 每个用例独立的临时目录
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name
        self.path = "demo.py"

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, content):
        full = os.path.join(self.tmpdir, self.path)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)

    def _read(self):
        full = os.path.join(self.tmpdir, self.path)
        with open(full, encoding="utf-8") as f:
            return f.read()

    # ---------- 正常替换 ----------
    def test_replace_success(self):
        self._write("def div(a, b):\n    return a / b\n\nprint(div(10, 2))\n")
        result = edit_file(self.path, "    return a / b",
                           "    return a * b", cwd=self.tmpdir)
        # 返回包含 success 标记
        self.assertIn("<success>", result)
        self.assertIn("已修改 demo.py", result)
        # 文件确实被改
        self.assertIn("    return a * b", self._read())
        self.assertNotIn("    return a / b", self._read())

    def test_replace_line_no_in_message(self):
        content = "line1\nline2\nline3\ntarget\n"
        self._write(content)
        result = edit_file(self.path, "target", "replaced",
                           cwd=self.tmpdir)
        # target 在第 4 行，行号 = 前面 \n 数量 + 1，第一个字符是 line1
        # content.index("target") 前有 3 个换行，行号应为 4
        self.assertIn("第 4 行", result)
        self.assertNotIn("target", self._read())
        self.assertIn("replaced", self._read())

    def test_replace_only_one_when_old_appears_once(self):
        # old 在文件中出现多次但给出了唯一上下文的情况本用例只验证单次出现直接替换
        self._write("x = 1\n")
        result = edit_file(self.path, "= 1", "= 2", cwd=self.tmpdir)
        self.assertIn("<success>", result)
        self.assertEqual("x = 2\n", self._read())

    # ---------- 找不到 old ----------
    def test_not_found(self):
        self._write("def div(a, b):\n    return a / b\n")
        result = edit_file(self.path, "return a * b", "xxx",
                           cwd=self.tmpdir)
        self.assertIn("<error>", result)
        self.assertIn("找不到", result)
        # 内容不变
        self.assertIn("    return a / b", self._read())

    def test_not_found_empty_file(self):
        self._write("")
        result = edit_file(self.path, "anything", "new", cwd=self.tmpdir)
        self.assertIn("<error>", result)
        self.assertEqual("", self._read())

    # ---------- old 出现多次 ----------
    def test_appears_multiple_times(self):
        self._write("x = 1\ny = 1\nz = 1\n")
        result = edit_file(self.path, "= 1", "= 2", cwd=self.tmpdir)
        self.assertIn("<error>", result)
        self.assertIn("3 次", result)   # 出现次数出现在消息里
        # 什么都没改
        self.assertEqual("x = 1\ny = 1\nz = 1\n", self._read())

    def test_appears_multiple_times_with_context_becomes_unique(self):
        # 多带上下文后 old 唯一，应当替换成功
        self._write("x = 1\ny = 1\nz = 1\n")
        result = edit_file(self.path, "x = 1", "x = 42", cwd=self.tmpdir)
        self.assertIn("<success>", result)
        self.assertEqual("x = 42\ny = 1\nz = 1\n", self._read())

    # ---------- 文件不存在 ----------
    def test_file_not_exist(self):
        result = edit_file("no_such.py", "old", "new", cwd=self.tmpdir)
        self.assertIn("<error>", result)
        self.assertIn("文件不存在", result)

    def test_file_not_exist_no_cwd(self):
        # 不带 cwd 时基于当前工作目录，这里用一个肯定不存在的随机名字
        result = edit_file("__definitely_not_exist_12345.py", "a", "b")
        self.assertIn("<error>", result)
        self.assertIn("文件不存在", result)

    # ---------- 不污染源码 ----------
    def test_source_not_modified(self):
        # 从源码目录读取原始内容，确保整个测试过程中没被动过
        src = os.path.join(MODULE_DIR, "v3_tools.py")
        with open(src, encoding="utf-8") as f:
            before = f.read()
        # 在这个用例里做一次正常替换（在临时目录）
        self._write("hello world\n")
        edit_file(self.path, "hello", "bye", cwd=self.tmpdir)
        with open(src, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after)


if __name__ == "__main__":
    sys.path.insert(0, os.getcwd())
    unittest.main()
