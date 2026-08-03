# src/analizadores/resumen.py

import pwd

from procfs import rss_a_bytes, total_jiffies


def calcular_cpu_percent(stat_actual, stat_anterior, cpu_actual, cpu_anterior):
    """Calcula CPU% del proceso entre dos snapshots consecutivos."""
    if not stat_anterior or not cpu_anterior:
        return 0.0

    delta_proceso = (
        stat_actual["utime"] + stat_actual["stime"]
        - stat_anterior["utime"] - stat_anterior["stime"]
    )
    delta_total = total_jiffies(cpu_actual) - total_jiffies(cpu_anterior)

    if delta_total <= 0 or delta_proceso < 0:
        return 0.0

    return (delta_proceso / delta_total) * 100.0


def obtener_identidad(status):
    uid = int(status.get("Uid", "0").split()[0])
    gid = int(status.get("Gid", "0").split()[0])
    try:
        usuario = pwd.getpwuid(uid).pw_name
    except KeyError:
        usuario = str(uid)
    return uid, gid, usuario


def construir_resumen(snapshot, snapshot_anterior=None):
    procesos = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        status = datos["status"]
        stat_anterior = None

        if snapshot_anterior and pid in snapshot_anterior.get("procesos", {}):
            stat_anterior = snapshot_anterior["procesos"][pid]["stat"]

        uid, gid, usuario = obtener_identidad(status)
        procesos.append({
            "pid": pid,
            "ppid": stat["ppid"],
            "uid": uid,
            "gid": gid,
            "usuario": usuario,
            "estado": stat["state"],
            "nombre": stat["comm"],
            "cmdline": datos["cmdline"] or stat["comm"],
            "threads": int(status.get("Threads", "0").split()[0]),
            "rss_paginas": stat["rss"],
            "rss_bytes": rss_a_bytes(stat["rss"]),
            "vsize": stat["vsize"],
            "utime": stat["utime"],
            "stime": stat["stime"],
            "cpu_percent": calcular_cpu_percent(
                stat,
                stat_anterior,
                snapshot["cpu"],
                snapshot_anterior["cpu"] if snapshot_anterior else None,
            ),
        })

    procesos.sort(key=lambda proceso: proceso["pid"])
    return procesos