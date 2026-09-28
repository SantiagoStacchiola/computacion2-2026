from collections import deque
import time


def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
        yield


def tarea_egoista(nombre):
    print(f'  [{nombre}] me pongo a calcular')

    time.sleep(3)

    print(f'  [{nombre}] listo')

    yield


def scheduler(tareas):
    pendientes = deque(tareas)

    while pendientes:
        t = pendientes.popleft()

        try:
            next(t)
            pendientes.append(t)

        except StopIteration:
            pass


scheduler([
    tarea('A', 3),
    tarea_egoista('EGO'),
    tarea('B', 3)
])