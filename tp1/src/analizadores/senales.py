# src/analizadores/senales.py

from procfs import decodificar_señales


def construir_senales(snapshot, snapshot_anterior=None):
    procesos_senales = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        status = datos["status"]

        # Extraer máscaras de señales
        sigblk = status.get("SigBlk", "0000000000000000")
        sigign = status.get("SigIgn", "0000000000000000")
        sigcgt = status.get("SigCgt", "0000000000000000")
        sigpnd = status.get("SigPnd", "0000000000000000")
        shdpnd = status.get("ShdPnd", "0000000000000000")

        proceso_senales = {
            "pid": pid,
            "nombre": stat["comm"],
            "sigblk": decodificar_señales(sigblk),
            "sigign": decodificar_señales(sigign),
            "sigcgt": decodificar_señales(sigcgt),
            "sigpnd": decodificar_señales(sigpnd),
            "shdpnd": decodificar_señales(shdpnd),
        }

        procesos_senales.append(proceso_senales)

    procesos_senales.sort(key=lambda p: p["pid"])
    return procesos_senales