#!/usr/bin/env python3
"""Interpretar señales como comandos."""
import signal
import time
import os

contador = 0
ultimo_tiempo = 0

VENTANA = 1.0  # segundos para agrupar señales


def handler(sig, frame):
    global contador, ultimo_tiempo

    ahora = time.time()

    # Si pasó mucho tiempo, reiniciar
    if ahora - ultimo_tiempo > VENTANA:
        contador = 0

    contador += 1
    ultimo_tiempo = ahora


def procesar_comando():
    global contador

    if contador == 1:
        print("[CMD] Acción A")
    elif contador == 2:
        print("[CMD] Acción B")
    elif contador >= 3:
        print("[CMD] Acción C")

    contador = 0


signal.signal(signal.SIGUSR1, handler)

print(f"PID: {os.getpid()}")
print("Mandá señales SIGUSR1 (rápido varias veces)")

while True:
    time.sleep(1)

    if contador > 0:
        procesar_comando()