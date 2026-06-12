#!/usr/bin/env python3
"""Watchdog que reinicia un proceso si muere."""
import os
import signal
import time

def lanzar_worker():
    pid = os.fork()

    if pid == 0:
        # === WORKER ===
        print(f"[WORKER] PID {os.getpid()} iniciado")

        # Simular trabajo + fallo
        for i in range(5):
            print(f"[WORKER] Trabajando... {i}")
            time.sleep(1)

        print("[WORKER] Simulando crash 😈")
        os._exit(1)

    return pid


def main():
    print(f"[WATCHDOG] PID {os.getpid()}")

    ejecutando = True

    def shutdown(sig, frame):
        nonlocal ejecutando
        print("\n[WATCHDOG] Apagando...")
        ejecutando = False

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    worker_pid = lanzar_worker()

    while ejecutando:
        pid, status = os.wait()

        if pid == worker_pid:
            codigo = os.WEXITSTATUS(status)
            print(f"[WATCHDOG] Worker murió (código {codigo})")

            if ejecutando:
                print("[WATCHDOG] Reiniciando worker...")
                worker_pid = lanzar_worker()

    # Cleanup
    try:
        os.kill(worker_pid, signal.SIGTERM)
    except:
        pass

    print("[WATCHDOG] Terminado")


if __name__ == "__main__":
    main()