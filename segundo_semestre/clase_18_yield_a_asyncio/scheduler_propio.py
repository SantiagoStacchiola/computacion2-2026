from collections import deque


def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
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
    tarea('B', 2),
    tarea('C', 4)
])