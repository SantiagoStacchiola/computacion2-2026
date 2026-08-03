# src/analizadores/sistema.py

from analizadores.resumen import calcular_cpu_percent
from procfs import leer_btime, leer_loadavg, leer_uptime, rss_a_bytes, total_jiffies


def calcular_cpu_percent_global(cpu_actual, cpu_anterior):
    if not cpu_anterior:
        return {"user": 0.0, "system": 0.0, "idle": 0.0, "iowait": 0.0}

    delta_total = total_jiffies(cpu_actual) - total_jiffies(cpu_anterior)
    if delta_total <= 0:
        return {"user": 0.0, "system": 0.0, "idle": 0.0, "iowait": 0.0}

    return {
        clave: ((cpu_actual.get(clave, 0) - cpu_anterior.get(clave, 0)) / delta_total) * 100.0
        for clave in ("user", "system", "idle", "iowait")
    }


def construir_sistema(snapshot, snapshot_anterior=None):
    estados = {}
    threads_totales = 0
    ranking = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        estado = stat["state"]
        estados[estado] = estados.get(estado, 0) + 1
        threads_totales += int(datos["status"].get("Threads", "0").split()[0])

        stat_anterior = None
        if snapshot_anterior and pid in snapshot_anterior.get("procesos", {}):
            stat_anterior = snapshot_anterior["procesos"][pid]["stat"]

        ranking.append({
            "pid": pid,
            "nombre": stat["comm"],
            "cpu_percent": calcular_cpu_percent(
                stat,
                stat_anterior,
                snapshot["cpu"],
                snapshot_anterior["cpu"] if snapshot_anterior else None,
            ),
            "rss_bytes": rss_a_bytes(stat["rss"]),
        })

    return {
        "timestamp": snapshot["timestamp"],
        "cpu_percent": calcular_cpu_percent_global(
            snapshot["cpu"],
            snapshot_anterior["cpu"] if snapshot_anterior else None,
        ),
        "loadavg": leer_loadavg(),
        "uptime": leer_uptime(),
        "btime": leer_btime(),
        "memoria": snapshot["memoria"],
        "procesos_por_estado": estados,
        "zombies": estados.get("Z", 0),
        "threads_totales": threads_totales,
        "procesos_totales": len(snapshot["procesos"]),
        "top_cpu": sorted(ranking, key=lambda item: item["cpu_percent"], reverse=True)[:3],
        "top_memoria": sorted(ranking, key=lambda item: item["rss_bytes"], reverse=True)[:3],
    }