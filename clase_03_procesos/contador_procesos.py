#!/usr/bin/env python3
"""Contador de procesos en el sistema."""

import os

def contar_procesos():
    proc_path = "/proc"
    contador = 0

    for entrada in os.listdir(proc_path):
        if entrada.isdigit():  # solo nombres numéricos = PIDs
            contador += 1

    return contador


if __name__ == "__main__":
    total = contar_procesos()
    print(f"Cantidad de procesos en el sistema: {total}")