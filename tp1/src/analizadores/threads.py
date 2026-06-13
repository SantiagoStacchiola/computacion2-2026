# src/analizadores/threads.py

from procfs import leer_threads


def construir_threads(snapshot, snapshot_anterior=None):
    procesos_threads = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]

        threads = leer_threads(pid)

        proceso_threads = {
            "pid": pid,
            "nombre": stat["comm"],
            "num_threads": len(threads),
            "threads": threads,
        }

        procesos_threads.append(proceso_threads)

    procesos_threads.sort(key=lambda p: p["pid"])
    return procesos_threads