import time
from collections import deque


def dormir(segundos):
    yield time.monotonic() + segundos


def tarea(nombre, veces):
    for i in range(veces):
        print(f'  [{nombre}] {i}')

        yield from dormir(0.1)


def scheduler(tareas):
    pendientes = deque((0, t) for t in tareas)

    while pendientes:
        despertar, t = pendientes.popleft()

        ahora = time.monotonic()

        if ahora < despertar:
            pendientes.append((despertar, t))
            continue

        try:
            cuando = next(t)
            pendientes.append((cuando or 0, t))

        except StopIteration:
            pass


scheduler([
    tarea('A', 3),
    tarea('B', 3),
    tarea('C', 3)
])