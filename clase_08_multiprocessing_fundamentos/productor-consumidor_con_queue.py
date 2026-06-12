#!/usr/bin/env python3
"""Productor-consumidor con Queue."""

from multiprocessing import Process, Queue
import time

def productor(q):
    for i in range(10):
        print(f"[PRODUCTOR] Generando item {i}")
        q.put(i)
        time.sleep(0.5)

    q.put(None)  # señal de fin


def consumidor(q):
    while True:
        item = q.get()

        if item is None:
            break

        print(f"[CONSUMIDOR] Procesando item {item}")
        time.sleep(1)

    print("[CONSUMIDOR] Fin")


if __name__ == "__main__":
    q = Queue()

    p1 = Process(target=productor, args=(q,))
    p2 = Process(target=consumidor, args=(q,))

    p1.start()
    p2.start()

    p1.join()
    p2.join()