"""calc 模块的单元测试。"""
import unittest

from calc import add, div, mul, sub


class TestCalc(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(-1, 1), 0)
        self.assertEqual(add(0, 0), 0)

    def test_sub(self):
        self.assertEqual(sub(5, 3), 2)
        self.assertEqual(sub(0, 7), -7)

    def test_mul(self):
        self.assertEqual(mul(4, 3), 12)
        self.assertEqual(mul(0, 9), 0)
        self.assertEqual(mul(-2, 5), -10)

    def test_div(self):
        self.assertEqual(div(10, 2), 5)
        self.assertAlmostEqual(div(1, 3), 1 / 3)

    def test_div_by_zero(self):
        with self.assertRaises(ValueError):
            div(1, 0)


if __name__ == "__main__":
    unittest.main()
