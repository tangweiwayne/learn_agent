def div(a, b):
    if b == 0:
        raise ValueError(f"除数不能为 0（被除数 a={a}）")
    return a / b

print(div(10, 2))
print(div(5, 0))
