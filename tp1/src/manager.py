# src/manager.py

from multiprocessing import Manager, Value
import time


def crear_manager_compartido():
    """
    Crea el Manager dict compartido con estructura inicial.
    Cada vista tiene: data, timestamp, intervalo de refresco.
    """
    manager = Manager()
    
    snapshot = manager.dict()
    
    # Inicializar slots para cada analizador
    snapshot["resumen"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 2.0,
    })
    
    snapshot["memoria"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 3.0,
    })
    
    snapshot["fds"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 5.0,
    })
    
    snapshot["threads"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 2.0,
    })
    
    snapshot["senales"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 10.0,
    })
    
    snapshot["scheduling"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 10.0,
    })
    
    snapshot["sistema"] = manager.dict({
        "data": [],
        "ts": time.time(),
        "intervalo": 2.0,
    })
    
    # Estado global
    snapshot["estado_global"] = manager.dict({
        "vista_activa": "resumen",  # 1-7
        "filtro_comando": "",
        "filtro_usuario": "",
        "ordenar_por": "cpu_percent",  # o "rss_bytes", "pid"
        "pid_pinned": None,
        "verbose": False,
        "running": True,
    })
    
    return snapshot


def actualizar_vista(snapshot, nombre_vista, data, intervalo=None):
    """
    Actualiza atomicamente una vista en el snapshot.
    """
    vista = snapshot[nombre_vista]
    vista["data"] = data
    vista["ts"] = time.time()
    if intervalo is not None:
        vista["intervalo"] = intervalo
    snapshot[nombre_vista] = vista


def obtener_vista(snapshot, nombre_vista):
    """
    Obtiene una vista del snapshot de forma segura.
    """
    return {
        "data": list(snapshot[nombre_vista]["data"]),
        "ts": snapshot[nombre_vista]["ts"],
        "intervalo": snapshot[nombre_vista]["intervalo"],
    }