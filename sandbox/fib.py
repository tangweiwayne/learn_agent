def fib(n):
    a, b = 0, 1
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result

print("斐波那契数列前20项：")
for i, num in enumerate(fib(20), 1):
    print(f"第{i}项: {num}")
