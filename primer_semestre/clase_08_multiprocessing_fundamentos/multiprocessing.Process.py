#!/usr/bin/env python3
"""Versión multiprocessing del fork con wait."""

from multiprocessing import Process
import os

def trabajo_hijo():
    print(f"Hijo trabajando... PID={os.getpid()}")

    # Simular trabajo
    for i in range(3):
        print(f"  Hijo: paso {i+1}")

    print("Hijo terminando")


if __name__ == "__main__":
    print(f"Proceso original: PID={os.getpid()}")

    # Crear proceso hijo
    p = Process(target=trabajo_hijo)

    print("Padre iniciando hijo...")
    p.start()

    print(f"Padre esperando al hijo {p.pid}...")
    p.join()

    print(f"Padre: hijo terminó con código {p.exitcode}")