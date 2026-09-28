def contador():
    n = 0

    while True:
        print(f'  voy por {n}')
        yield
        n += 1


a = contador()
b = contador()

next(a)
next(b)

next(a)
next(b)

next(a)
next(b)