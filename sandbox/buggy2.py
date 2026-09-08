def div(a, b):
    if b == 0:
        raise ValueError("division by zero: divisor b must not be 0")
    return a / b

if __name__ == "__main__":
    print(div(10, 2))
    print(div(5, 0))
