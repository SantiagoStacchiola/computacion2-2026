# src/senales.py

import json
import time
from pathlib import Path


VISTAS = ("resumen", "memoria", "fds", "threads", "senales", "scheduling", "sistema")


def cargar_configuracion_desde_archivo(ruta_config):
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def recargar_configuracion(snapshot_global, intervalos, ruta_config):
    """Recarga filtros, vista, verbose e intervalos ante SIGHUP."""
    config = cargar_configuracion_desde_archivo(ruta_config)
    estado = snapshot_global["estado_global"]

    estado["vista_activa"] = config.get("default_view", estado.get("vista_activa", "resumen"))
    estado["filtro_comando"] = config.get("filters", {}).get("comando", "")
    estado["filtro_usuario"] = config.get("filters", {}).get("usuario", "")
    estado["ordenar_por"] = config.get("ordering", estado.get("ordenar_por", "cpu_percent"))
    estado["verbose"] = bool(config.get("verbose", estado.get("verbose", False)))
    estado["config_version"] = int(estado.get("config_version", 0)) + 1
    estado["redibujar"] = True
    estado["ultimo_evento"] = "SIGHUP: configuración recargada"

    for vista, valor in intervalos.items():
        if vista in config.get("intervals", {}):
            with valor.get_lock():
                valor.value = float(config["intervals"][vista])

    return config


def _convertir_para_json(valor):
    if isinstance(valor, dict):
        return {clave: _convertir_para_json(dato) for clave, dato in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_convertir_para_json(dato) for dato in valor]
    if isinstance(valor, set):
        return sorted(_convertir_para_json(dato) for dato in valor)
    return valor


def dumpear_snapshot(snapshot_global, ruta_salida):
    snapshot = {}
    for clave in (*VISTAS, "estado_global"):
        snapshot[clave] = _convertir_para_json(dict(snapshot_global[clave]))

    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        json.dump(snapshot, archivo, indent=2, ensure_ascii=False)


def alternar_verbose(snapshot_global):
    estado = snapshot_global["estado_global"]
    estado["verbose"] = not bool(estado.get("verbose", False))
    estado["redibujar"] = True
    estado["ultimo_evento"] = f"SIGUSR2: verbose={estado['verbose']}"


def pedir_redibujado(snapshot_global):
    estado = snapshot_global["estado_global"]
    estado["redibujar"] = True


def ruta_dump_con_timestamp():
    marca = time.strftime("%Y%m%d_%H%M%S")
    return Path(f"dump_{marca}.json")