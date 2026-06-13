# src/analizadores/memoria.py

from procfs import leer_maps, extraer_memoria_de_status


def contar_page_faults(stat):
    """
    Extrae faults menores y mayores desde /proc/[pid]/stat.
    """
    return {
        "minor_faults": int(stat.get("minflt", 0)),
        "major_faults": int(stat.get("majflt", 0)),
    }


def construir_memoria(snapshot, snapshot_anterior=None):
    procesos_memoria = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        status = datos["status"]

        memoria = extraer_memoria_de_status(status)
        faults = contar_page_faults(stat)
        mapeos = leer_maps(pid)

        segmentos_agrupados = {}
        for mapeo in mapeos:
            path = mapeo["path"] or "[anon]"

            if "[heap]" in path:
                tipo = "heap"
            elif "[stack" in path:
                tipo = "stack"
            elif "[vdso]" in path:
                tipo = "vdso"
            elif "[vsyscall]" in path:
                tipo = "vsyscall"
            elif path.startswith("/"):
                tipo = "file"
            else:
                tipo = "other"

            if tipo not in segmentos_agrupados:
                segmentos_agrupados[tipo] = {
                    "tamano": 0,
                    "permisos": set(),
                    "count": 0,
                }

            segmentos_agrupados[tipo]["tamano"] += mapeo["tamano"]
            segmentos_agrupados[tipo]["permisos"].add(mapeo["permisos"])
            segmentos_agrupados[tipo]["count"] += 1

        for tipo in segmentos_agrupados:
            segmentos_agrupados[tipo]["permisos"] = list(
                segmentos_agrupados[tipo]["permisos"]
            )

        proceso_memoria = {
            "pid": pid,
            "nombre": stat["comm"],
            "memoria_campos": memoria,
            "faults": faults,
            "segmentos_agrupados": segmentos_agrupados,
            "total_mapeos": len(mapeos),
        }

        procesos_memoria.append(proceso_memoria)

    procesos_memoria.sort(key=lambda p: p["pid"])
    return procesos_memoria