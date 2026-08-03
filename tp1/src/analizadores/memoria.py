# src/analizadores/memoria.py

from procfs import extraer_memoria_de_status, leer_maps


def contar_page_faults(stat):
    return {
        "minor_faults": int(stat.get("minflt", 0)),
        "children_minor_faults": int(stat.get("cminflt", 0)),
        "major_faults": int(stat.get("majflt", 0)),
        "children_major_faults": int(stat.get("cmajflt", 0)),
    }


def clasificar_segmento(mapeo):
    path = mapeo["path"] or "[anon]"
    permisos = mapeo["permisos"]

    if "[heap]" in path:
        return "heap"
    if "[stack" in path:
        return "stack"
    if "s" in permisos:
        return "shared"
    if "x" in permisos:
        return "text"
    if "w" in permisos:
        return "data"
    return "other"


def construir_memoria(snapshot, snapshot_anterior=None):
    procesos = []

    for pid, datos in snapshot["procesos"].items():
        stat = datos["stat"]
        mapeos = leer_maps(pid)
        agrupados = {}

        for mapeo in mapeos:
            tipo = clasificar_segmento(mapeo)
            grupo = agrupados.setdefault(tipo, {
                "tamano": 0,
                "permisos": set(),
                "count": 0,
            })
            grupo["tamano"] += mapeo["tamano"]
            grupo["permisos"].add(mapeo["permisos"])
            grupo["count"] += 1

        for grupo in agrupados.values():
            grupo["permisos"] = sorted(grupo["permisos"])

        procesos.append({
            "pid": pid,
            "nombre": stat["comm"],
            "memoria_campos": extraer_memoria_de_status(datos["status"]),
            "faults": contar_page_faults(stat),
            "segmentos_agrupados": agrupados,
            "total_mapeos": len(mapeos),
        })

    procesos.sort(key=lambda proceso: proceso["pid"])
    return procesos