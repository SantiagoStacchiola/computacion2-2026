#!/usr/bin/env python3
"""5 workers en paralelo."""

from multiprocessing import Process
import time
import random
import os

def worker(numero):
    duracion = random.uniform(0.5, 2)

    print(f"[Worker {numero}] PID={os.getpid()} durmiendo {duracion:.2f}s")

    time.sleep(duracion)

    print(f"[Worker {numero}] Terminado")


if __name__ == "__main__":
    inicio = time.time()

    procesos = []

    # lanzar workers
    for i in range(5):
        p = Process(target=worker, args=(i,))
        p.start()
        procesos.append(p)

    # esperar todos
    for p in procesos:
        p.join()

    duracion = time.time() - inicio

    print(f"\nTiempo total: {duracion:.2f}s")