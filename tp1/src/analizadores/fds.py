# src/analizadores/fds.py

from procfs import leer_fds


def construir_fds(snapshot, snapshot_anterior=None):
    procesos_fds = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]

        fds = leer_fds(pid)

        # Contar por tipo
        tipos = {}
        for fd in fds:
            tipo = fd["tipo"]
            tipos[tipo] = tipos.get(tipo, 0) + 1

        proceso_fds = {
            "pid": pid,
            "nombre": stat["comm"],
            "total_fds": len(fds),
            "fds_por_tipo": tipos,
            "fds": fds,
        }

        procesos_fds.append(proceso_fds)

    procesos_fds.sort(key=lambda p: p["pid"])
    return procesos_fds