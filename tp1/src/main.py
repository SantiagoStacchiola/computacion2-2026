# src/main.py

import signal
import time
import sys
from multiprocessing import Process
from manager import crear_manager_compartido, actualizar_vista, obtener_vista
from recolector import recolectar
from analizadores.resumen import construir_resumen
from analizadores.memoria import construir_memoria
from analizadores.sistema import construir_sistema
from analizadores.fds import construir_fds
from analizadores.threads import construir_threads
from analizadores.scheduling import construir_scheduling
from analizadores.senales import construir_senales
from display import iniciar_display


# Variables globales para signal handling
snapshot_global = None
workers = []
running = True


def signal_handler(signum, frame):
    """
    Manejador de señales async-safe.
    """
    global running
    if signum in (signal.SIGINT, signal.SIGTERM):
        print("\n[MAIN] Recibido SIGINT/SIGTERM, iniciando shutdown...")
        running = False
        if snapshot_global:
            snapshot_global["estado_global"]["running"] = False
    elif signum == signal.SIGUSR1:
        print("[MAIN] Recibido SIGUSR1, dumpeando snapshot...")
        # TODO: implementar dump a JSON
    elif signum == signal.SIGUSR2:
        print("[MAIN] Recibido SIGUSR2, toggling verbose...")
        if snapshot_global:
            estado = snapshot_global["estado_global"]
            estado["verbose"] = not estado["verbose"]
            snapshot_global["estado_global"] = estado


def worker_resumen(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Resumen."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_resumen(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "resumen", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["resumen"]["intervalo"]
            time.sleep(max(0.5, intervalo))
        except Exception as e:
            print(f"[RESUMEN] Error: {e}")
            time.sleep(1)


def worker_memoria(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Memoria."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_memoria(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "memoria", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["memoria"]["intervalo"]
            time.sleep(max(1.0, intervalo))
        except Exception as e:
            print(f"[MEMORIA] Error: {e}")
            time.sleep(1)


def worker_fds(snapshot, snapshot_anterior):
    """Worker que actualiza la vista FDs."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_fds(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "fds", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["fds"]["intervalo"]
            time.sleep(max(2.0, intervalo))
        except Exception as e:
            print(f"[FDS] Error: {e}")
            time.sleep(1)


def worker_threads(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Threads."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_threads(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "threads", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["threads"]["intervalo"]
            time.sleep(max(0.5, intervalo))
        except Exception as e:
            print(f"[THREADS] Error: {e}")
            time.sleep(1)


def worker_scheduling(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Scheduling."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_scheduling(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "scheduling", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["scheduling"]["intervalo"]
            time.sleep(max(5.0, intervalo))
        except Exception as e:
            print(f"[SCHEDULING] Error: {e}")
            time.sleep(1)


def worker_senales(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Señales."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_senales(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "senales", data)
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["senales"]["intervalo"]
            time.sleep(max(5.0, intervalo))
        except Exception as e:
            print(f"[SENALES] Error: {e}")
            time.sleep(1)


def worker_sistema(snapshot, snapshot_anterior):
    """Worker que actualiza la vista Sistema."""
    while snapshot["estado_global"]["running"]:
        try:
            snap_nuevo = recolectar()
            data = construir_sistema(snap_nuevo, snapshot_anterior)
            actualizar_vista(snapshot, "sistema", [data])
            snapshot_anterior.clear()
            snapshot_anterior.update(snap_nuevo)
            
            intervalo = snapshot["sistema"]["intervalo"]
            time.sleep(max(1.0, intervalo))
        except Exception as e:
            print(f"[SISTEMA] Error: {e}")
            time.sleep(1)


def main():
    global snapshot_global, workers, running
    
    print("=== Monitor de Procesos - Inicializando ===\n")
    
    # Crear manager compartido
    snapshot_global = crear_manager_compartido()
    
    # Registrar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)
    
    # Crear snapshots anteriores para cada worker
    snap_resumen_ant = {}
    snap_memoria_ant = {}
    snap_fds_ant = {}
    snap_threads_ant = {}
    snap_scheduling_ant = {}
    snap_senales_ant = {}
    snap_sistema_ant = {}
    
    # Crear workers
    print("[MAIN] Lanzando 7 workers...")
    workers = [
        Process(target=worker_resumen, args=(snapshot_global, snap_resumen_ant), name="worker-resumen"),
        Process(target=worker_memoria, args=(snapshot_global, snap_memoria_ant), name="worker-memoria"),
        Process(target=worker_fds, args=(snapshot_global, snap_fds_ant), name="worker-fds"),
        Process(target=worker_threads, args=(snapshot_global, snap_threads_ant), name="worker-threads"),
        Process(target=worker_scheduling, args=(snapshot_global, snap_scheduling_ant), name="worker-scheduling"),
        Process(target=worker_senales, args=(snapshot_global, snap_senales_ant), name="worker-senales"),
        Process(target=worker_sistema, args=(snapshot_global, snap_sistema_ant), name="worker-sistema"),
    ]
    
    for w in workers:
        w.daemon = False
        w.start()
        print(f"  ✓ {w.name} iniciado (PID {w.pid})")
    
    print("\n[MAIN] Workers corriendo. Presiona Ctrl+C para salir.\n")
    
        # Iniciar display en hilo principal
    try:
        iniciar_display(snapshot_global)
    except KeyboardInterrupt:
        pass

    # Cleanup
    print("\n[MAIN] Terminando workers...")
    snapshot_global["estado_global"]["running"] = False

    for w in workers:
        w.join(timeout=5)
        if w.is_alive():
            print(f"  ! {w.name} no terminó, forzando kill...")
            w.terminate()
            w.join()
        else:
            print(f"  ✓ {w.name} terminado")

    print("[MAIN] Monitor cerrado.")


if __name__ == "__main__":
    main()