# src/analizadores/sistema.py

from procfs import leer_loadavg, leer_uptime, leer_btime


def calcular_cpu_percent_global(cpu_actual, cpu_anterior):
    """
    Calcula porcentajes de CPU global (user, system, idle, iowait).
    """
    if not cpu_anterior:
        return {"user": 0, "system": 0, "idle": 0, "iowait": 0}

    delta_user = cpu_actual["user"] - cpu_anterior["user"]
    delta_system = cpu_actual["system"] - cpu_anterior["system"]
    delta_idle = cpu_actual["idle"] - cpu_anterior["idle"]
    delta_iowait = cpu_actual["iowait"] - cpu_anterior["iowait"]

    delta_total = delta_user + delta_system + delta_idle + delta_iowait + \
                  (cpu_actual["nice"] - cpu_anterior["nice"]) + \
                  (cpu_actual["irq"] - cpu_anterior["irq"]) + \
                  (cpu_actual["softirq"] - cpu_anterior["softirq"])

    if delta_total <= 0:
        return {"user": 0, "system": 0, "idle": 0, "iowait": 0}

    return {
        "user": (delta_user / delta_total) * 100,
        "system": (delta_system / delta_total) * 100,
        "idle": (delta_idle / delta_total) * 100,
        "iowait": (delta_iowait / delta_total) * 100,
    }


def contar_procesos_por_estado(procesos):
    """
    Cuenta procesos por estado (R/S/D/T/Z).
    """
    estados = {}

    for pid, datos in procesos.items():
        estado = datos["stat"]["state"]
        estados[estado] = estados.get(estado, 0) + 1

    return estados


def construir_sistema(snapshot, snapshot_anterior=None):
    """
    Construye vista de sistema global.
    """
    loadavg = leer_loadavg()
    uptime = leer_uptime()
    btime = leer_btime()

    cpu_percent = calcular_cpu_percent_global(
        snapshot["cpu"],
        snapshot_anterior["cpu"] if snapshot_anterior else None
    )

    estados = contar_procesos_por_estado(snapshot["procesos"])

    threads_totales = sum(
        int(datos["status"].get("Threads", 0))
        for datos in snapshot["procesos"].values()
    )

    return {
        "timestamp": snapshot["timestamp"],
        "cpu_percent": cpu_percent,
        "loadavg": loadavg,
        "uptime": uptime,
        "btime": btime,
        "memoria": snapshot["memoria"],
        "procesos_por_estado": estados,
        "threads_totales": threads_totales,
        "procesos_totales": len(snapshot["procesos"]),
    }