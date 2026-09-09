def div(a, b):
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b

print(div(10, 2))
try:
    print(div(5, 0))
except ValueError as e:
    print(f"捕获异常: {e}")
