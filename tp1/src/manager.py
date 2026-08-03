# src/manager.py

import time
from multiprocessing import Manager
from queue import Empty


DEFAULT_INTERVALS = {
    "resumen": 2.0,
    "memoria": 3.0,
    "fds": 5.0,
    "threads": 2.0,
    "senales": 10.0,
    "scheduling": 10.0,
    "sistema": 2.0,
}


VISTAS = tuple(DEFAULT_INTERVALS)


def crear_manager_compartido(config=None):
    """Crea el snapshot global compartido mediante multiprocessing.Manager."""
    config = config or {}
    manager = Manager()
    snapshot = manager.dict()

    for nombre_vista in VISTAS:
        dato_inicial = {} if nombre_vista == "sistema" else []
        snapshot[nombre_vista] = manager.dict({
            "data": dato_inicial,
            "ts": 0.0,
            "version": 0,
        })

    snapshot["estado_global"] = manager.dict({
        "vista_activa": config.get("default_view", "resumen"),
        "filtro_comando": config.get("filters", {}).get("comando", ""),
        "filtro_usuario": config.get("filters", {}).get("usuario", ""),
        "ordenar_por": config.get("ordering", "cpu_percent"),
        "pid_pinned": None,
        "verbose": bool(config.get("verbose", False)),
        "running": True,
        "redibujar": True,
        "ultimo_evento": "",
        "config_version": 0,
    })

    # Se devuelve también el Manager para conservar una referencia explícita
    # durante toda la ejecución del programa.
    return manager, snapshot


def actualizar_vista(snapshot, nombre_vista, data, timestamp=None):
    """Actualiza una vista completa y aumenta su versión."""
    vista = snapshot[nombre_vista]
    vista["data"] = data
    vista["ts"] = timestamp if timestamp is not None else time.time()
    vista["version"] = int(vista.get("version", 0)) + 1


def ciclo_agregador(snapshot, cola_resultados):
    """Único proceso que escribe resultados de analizadores en el snapshot."""
    while snapshot["estado_global"].get("running", True):
        try:
            nombre_vista, data, timestamp = cola_resultados.get(timeout=0.5)
        except Empty:
            continue

        actualizar_vista(snapshot, nombre_vista, data, timestamp)