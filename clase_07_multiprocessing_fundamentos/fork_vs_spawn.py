#!/usr/bin/env python3
"""Comparar fork vs spawn."""

import multiprocessing as mp
import time

def tarea():
    pass


def benchmark(method):
    mp.set_start_method(method, force=True)

    procesos = []

    inicio = time.time()

    for _ in range(100):
        p = mp.Process(target=tarea)
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

    duracion = time.time() - inicio

    print(f"{method}: {duracion:.4f}s")


if __name__ == "__main__":
    benchmark("fork")
    benchmark("spawn")