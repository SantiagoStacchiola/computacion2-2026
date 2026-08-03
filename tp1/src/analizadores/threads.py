# src/analizadores/threads.py

from procfs import leer_threads, total_jiffies


_historial_threads = {}
_cpu_anterior = None


def construir_threads(snapshot, snapshot_anterior=None):
    global _historial_threads, _cpu_anterior

    procesos = []
    historial_actual = {}
    delta_cpu = 0

    if _cpu_anterior:
        delta_cpu = total_jiffies(snapshot["cpu"]) - total_jiffies(_cpu_anterior)

    for pid, datos in snapshot["procesos"].items():
        threads = leer_threads(pid)
        historial_actual[pid] = {}

        for thread in threads:
            tid = thread["tid"]
            anterior = _historial_threads.get(pid, {}).get(tid)
            cpu_percent = 0.0

            if anterior and delta_cpu > 0:
                delta_thread = (
                    thread["utime"] + thread["stime"]
                    - anterior["utime"] - anterior["stime"]
                )
                if delta_thread >= 0:
                    cpu_percent = (delta_thread / delta_cpu) * 100.0

            thread["cpu_percent"] = cpu_percent
            historial_actual[pid][tid] = {
                "utime": thread["utime"],
                "stime": thread["stime"],
            }

        procesos.append({
            "pid": pid,
            "nombre": datos["stat"]["comm"],
            "num_threads": len(threads),
            "threads": threads,
        })

    _historial_threads = historial_actual
    _cpu_anterior = dict(snapshot["cpu"])
    procesos.sort(key=lambda proceso: proceso["pid"])
    return procesos