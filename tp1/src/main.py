# src/main.py

import json
import os
import select
import signal
import threading
import time
from multiprocessing import Process, Queue, Value
from pathlib import Path
from queue import Empty, Full

from analizadores.fds import construir_fds
from analizadores.memoria import construir_memoria
from analizadores.resumen import construir_resumen
from analizadores.scheduling import construir_scheduling
from analizadores.senales import construir_senales
from analizadores.sistema import construir_sistema
from analizadores.threads import construir_threads
from display import iniciar_display
from manager import ciclo_agregador, crear_manager_compartido
from recolector import recolectar
from senales import (
    alternar_verbose,
    dumpear_snapshot,
    pedir_redibujado,
    recargar_configuracion,
    ruta_dump_con_timestamp,
)


snapshot_global = None
intervalos_global = None
procesos_hijos = []
running = True
signal_wakeup_rfd = None
signal_wakeup_wfd = None


INTERVALOS_MINIMOS = {
    "resumen": 0.5,
    "memoria": 1.0,
    "fds": 2.0,
    "threads": 0.5,
    "senales": 5.0,
    "scheduling": 5.0,
    "sistema": 1.0,
}


def cargar_configuracion(ruta="config.json"):
    ruta_config = Path(__file__).resolve().parent.parent / ruta
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def poner_ultimo(cola, elemento):
    """Mantiene solamente el snapshot más reciente en una cola acotada."""
    try:
        cola.put_nowait(elemento)
        return
    except Full:
        pass

    try:
        cola.get_nowait()
    except Empty:
        pass

    try:
        cola.put_nowait(elemento)
    except Full:
        pass


def colector_central(snapshot, colas_vistas):
    """Lee /proc una vez y distribuye el último snapshot a los analizadores."""
    while snapshot["estado_global"].get("running", True):
        inicio = time.monotonic()
        try:
            snap_nuevo = recolectar()

            for cola in colas_vistas:
                poner_ultimo(cola, snap_nuevo)
        except Exception as error:
            estado = snapshot["estado_global"]
            estado["ultimo_evento"] = f"Recolector: {type(error).__name__}"

        restante = 0.5 - (time.monotonic() - inicio)
        if restante > 0:
            time.sleep(restante)


def leer_intervalo(valor_compartido, minimo):
    with valor_compartido.get_lock():
        return max(minimo, float(valor_compartido.value))


def ciclo_analizador(
    cola_entrada,
    cola_resultados,
    snapshot,
    nombre_vista,
    construir_fn,
    intervalo_compartido,
    minimo_intervalo,
):
    """Ejecuta un analizador con su propio ritmo de refresco."""
    snapshot_actual = None
    snapshot_anterior = None
    proximo_refresco = 0.0

    while snapshot["estado_global"].get("running", True):
        ahora = time.monotonic()
        espera = max(0.0, min(0.5, proximo_refresco - ahora))

        try:
            snapshot_actual = cola_entrada.get(timeout=espera)
            while True:
                snapshot_actual = cola_entrada.get_nowait()
        except Empty:
            pass

        ahora = time.monotonic()
        if snapshot_actual is None or ahora < proximo_refresco:
            continue

        try:
            data = construir_fn(snapshot_actual, snapshot_anterior)
            cola_resultados.put(
                (nombre_vista, data, time.time()),
                timeout=0.5,
            )
            snapshot_anterior = snapshot_actual
        except Full:
            pass
        except Exception as error:
            estado = snapshot["estado_global"]
            estado["ultimo_evento"] = (
                f"{nombre_vista}: {type(error).__name__}"
            )

        intervalo = leer_intervalo(intervalo_compartido, minimo_intervalo)
        proximo_refresco = ahora + intervalo


def worker_resumen(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "resumen",
        construir_resumen, intervalo, INTERVALOS_MINIMOS["resumen"],
    )


def worker_memoria(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "memoria",
        construir_memoria, intervalo, INTERVALOS_MINIMOS["memoria"],
    )


def worker_fds(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "fds",
        construir_fds, intervalo, INTERVALOS_MINIMOS["fds"],
    )


def worker_threads(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "threads",
        construir_threads, intervalo, INTERVALOS_MINIMOS["threads"],
    )


def worker_senales(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "senales",
        construir_senales, intervalo, INTERVALOS_MINIMOS["senales"],
    )


def worker_scheduling(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "scheduling",
        construir_scheduling, intervalo, INTERVALOS_MINIMOS["scheduling"],
    )


def worker_sistema(entrada, resultados, snapshot, intervalo):
    ciclo_analizador(
        entrada, resultados, snapshot, "sistema",
        construir_sistema, intervalo, INTERVALOS_MINIMOS["sistema"],
    )


def signal_handler(signum, frame):
    """Handler mínimo: signal.set_wakeup_fd escribe el número en el pipe."""
    return None


def procesar_senal(signum):
    global running

    if signum in (signal.SIGINT, signal.SIGTERM):
        running = False
        if snapshot_global is not None:
            estado = snapshot_global["estado_global"]
            estado["running"] = False
            estado["ultimo_evento"] = "Shutdown solicitado"

    elif signum == signal.SIGHUP and snapshot_global is not None:
        ruta = Path(__file__).resolve().parent.parent / "config.json"
        recargar_configuracion(snapshot_global, intervalos_global, ruta)

    elif signum == signal.SIGUSR1 and snapshot_global is not None:
        ruta = ruta_dump_con_timestamp()
        dumpear_snapshot(snapshot_global, ruta)
        estado = snapshot_global["estado_global"]
        estado["ultimo_evento"] = f"Dump creado: {ruta.name}"
        estado["redibujar"] = True

    elif signum == signal.SIGUSR2 and snapshot_global is not None:
        alternar_verbose(snapshot_global)

    elif signum == signal.SIGWINCH and snapshot_global is not None:
        pedir_redibujado(snapshot_global)


def hilo_manejo_senales():
    global signal_wakeup_rfd

    while running:
        try:
            listos, _, _ = select.select([signal_wakeup_rfd], [], [], 0.5)
            if not listos:
                continue

            for byte in os.read(signal_wakeup_rfd, 1024):
                procesar_senal(byte)
        except (OSError, ValueError):
            break


def configurar_senales():
    global signal_wakeup_rfd, signal_wakeup_wfd

    signal_wakeup_rfd, signal_wakeup_wfd = os.pipe()
    os.set_blocking(signal_wakeup_rfd, False)
    os.set_blocking(signal_wakeup_wfd, False)
    signal.set_wakeup_fd(signal_wakeup_wfd, warn_on_full_buffer=False)

    for nombre in ("SIGINT", "SIGTERM", "SIGHUP", "SIGUSR1", "SIGUSR2", "SIGWINCH"):
        signal.signal(getattr(signal, nombre), signal_handler)


def main():
    global snapshot_global, intervalos_global, procesos_hijos, running

    print("=== Monitor de Procesos - Inicializando ===\n")
    config = cargar_configuracion()
    manager, snapshot_global = crear_manager_compartido(config)

    intervalos_global = {
        vista: Value("d", float(config.get("intervals", {}).get(vista, minimo)))
        for vista, minimo in INTERVALOS_MINIMOS.items()
    }

    colas = {vista: Queue(maxsize=1) for vista in INTERVALOS_MINIMOS}
    cola_resultados = Queue(maxsize=50)

    procesos_hijos = [
        Process(
            target=colector_central,
            args=(snapshot_global, list(colas.values())),
            name="collector",
        ),
        Process(
            target=ciclo_agregador,
            args=(snapshot_global, cola_resultados),
            name="aggregator",
        ),
        Process(target=worker_resumen, args=(colas["resumen"], cola_resultados, snapshot_global, intervalos_global["resumen"]), name="worker-resumen"),
        Process(target=worker_memoria, args=(colas["memoria"], cola_resultados, snapshot_global, intervalos_global["memoria"]), name="worker-memoria"),
        Process(target=worker_fds, args=(colas["fds"], cola_resultados, snapshot_global, intervalos_global["fds"]), name="worker-fds"),
        Process(target=worker_threads, args=(colas["threads"], cola_resultados, snapshot_global, intervalos_global["threads"]), name="worker-threads"),
        Process(target=worker_senales, args=(colas["senales"], cola_resultados, snapshot_global, intervalos_global["senales"]), name="worker-senales"),
        Process(target=worker_scheduling, args=(colas["scheduling"], cola_resultados, snapshot_global, intervalos_global["scheduling"]), name="worker-scheduling"),
        Process(target=worker_sistema, args=(colas["sistema"], cola_resultados, snapshot_global, intervalos_global["sistema"]), name="worker-sistema"),
    ]

    print("[MAIN] Lanzando recolector, agregador y 7 analizadores...")
    for proceso in procesos_hijos:
        proceso.start()
        print(f"  ✓ {proceso.name} iniciado (PID {proceso.pid})")

    # Se configura después de iniciar los hijos para que ellos conserven los
    # handlers por defecto y puedan terminar correctamente con SIGTERM.
    configurar_senales()
    vigilante = threading.Thread(
        target=hilo_manejo_senales,
        name="signal-watcher",
        daemon=True,
    )
    vigilante.start()

    print("\n[MAIN] Procesos corriendo. Presiona q o Ctrl+C para salir.\n")

    try:
        iniciar_display(snapshot_global, intervalos_global)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        estado = snapshot_global["estado_global"]
        estado["running"] = False

        for proceso in procesos_hijos:
            proceso.join(timeout=3)
            if proceso.is_alive():
                proceso.terminate()
                proceso.join(timeout=2)
            if proceso.is_alive():
                proceso.kill()
                proceso.join(timeout=1)

        signal.set_wakeup_fd(-1)
        for descriptor in (signal_wakeup_rfd, signal_wakeup_wfd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass

        manager.shutdown()
        print("[MAIN] Monitor cerrado.")


if __name__ == "__main__":
    main()