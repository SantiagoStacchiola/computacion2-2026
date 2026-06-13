# src/recolector.py

import time
from procfs import (
    obtener_pids,
    leer_cpu_global,
    leer_meminfo,
    leer_stat,
    leer_status,
    leer_cmdline,
)


def recolectar():
    snapshot = {
        "timestamp": time.time(),
        "cpu": leer_cpu_global(),
        "memoria": leer_meminfo(),
        "procesos": {},
    }

    for pid in obtener_pids():
        try:
            snapshot["procesos"][pid] = {
                "stat": leer_stat(pid),
                "status": leer_status(pid),
                "cmdline": leer_cmdline(pid),
            }
        except (FileNotFoundError, ProcessLookupError, ValueError):
            pass

    return snapshot