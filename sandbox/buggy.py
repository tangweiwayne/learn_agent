def div(a, b):
    if b == 0:
        raise ValueError("除数不能为0")
    return a / b

if __name__ == "__main__":
    print(div(10, 2))
    print(div(5, 0))
