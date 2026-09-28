def fibonacci(limite=None):
    a, b = 0, 1

    while limite is None or a <= limite:
        yield a
        a, b = b, a + b


# Generador infinito
fib = fibonacci()

print("Primeros 10 números de Fibonacci:")
for _ in range(10):
    print(next(fib))

print("Siguientes dos:")
print(next(fib))
print(next(fib))


# Generador con límite
print("\nFibonacci hasta 100:")
for n in fibonacci(limite=100):
    print(n)