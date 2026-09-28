def acumulador():
    total = 0

    while True:
        n = yield total
        total += n


a = acumulador()

print("next:", next(a))

print("send 10:", a.send(10))
print("send 5:", a.send(5))
print("send 20:", a.send(20))