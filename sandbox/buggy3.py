def div(a, b):
    if b == 0:
        raise ValueError("除数不能为 0")
    return a / b

print(div(10, 2))
print(div(5, 0))
