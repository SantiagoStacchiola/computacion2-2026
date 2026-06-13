# src/analizadores/resumen.py

from procfs import rss_a_bytes


def calcular_cpu_percent(stat_actual, stat_anterior, cpu_actual, cpu_anterior):
    """
    Calcula el porcentaje de CPU usado por un proceso entre dos snapshots.
    """
    if not stat_anterior or not cpu_anterior:
        return 0.0

    delta_utime_stime = (stat_actual["utime"] + stat_actual["stime"]) - \
                        (stat_anterior["utime"] + stat_anterior["stime"])

    delta_cpu_total = (cpu_actual["user"] + cpu_actual["nice"] + 
                       cpu_actual["system"] + cpu_actual["idle"] + 
                       cpu_actual["iowait"] + cpu_actual["irq"] + 
                       cpu_actual["softirq"]) - \
                      (cpu_anterior["user"] + cpu_anterior["nice"] + 
                       cpu_anterior["system"] + cpu_anterior["idle"] + 
                       cpu_anterior["iowait"] + cpu_anterior["irq"] + 
                       cpu_anterior["softirq"])

    if delta_cpu_total <= 0:
        return 0.0

    return (delta_utime_stime / delta_cpu_total) * 100


def construir_resumen(snapshot, snapshot_anterior=None):
    procesos_resumen = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        status = datos["status"]

        # Obtener datos anteriores si existen
        stat_anterior = None
        if snapshot_anterior and pid in snapshot_anterior["procesos"]:
            stat_anterior = snapshot_anterior["procesos"][pid]["stat"]

        cpu_percent = calcular_cpu_percent(
            stat, 
            stat_anterior, 
            snapshot["cpu"], 
            snapshot_anterior["cpu"] if snapshot_anterior else None
        )

        proceso = {
            "pid": pid,
            "ppid": stat["ppid"],
            "estado": stat["state"],
            "nombre": stat["comm"],
            "cmdline": datos["cmdline"] or stat["comm"],
            "threads": int(status.get("Threads", 0)),
            "rss_paginas": stat["rss"],
            "rss_bytes": rss_a_bytes(stat["rss"]),
            "vsize": stat["vsize"],
            "utime": stat["utime"],
            "stime": stat["stime"],
            "cpu_percent": cpu_percent,
        }

        procesos_resumen.append(proceso)

    procesos_resumen.sort(key=lambda p: p["pid"])
    return procesos_resumen