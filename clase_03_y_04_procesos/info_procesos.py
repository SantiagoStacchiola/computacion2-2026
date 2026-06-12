#!/usr/bin/env python3
"""Información de un proceso dado su PID."""

import os
import sys

def info_proceso(pid):
    base = f"/proc/{pid}"

    if not os.path.exists(base):
        print(f"Error: el proceso {pid} no existe")
        return

    print(f"=== Información del proceso {pid} ===\n")

    # 📌 1. cmdline (comando completo)
    try:
        with open(f"{base}/cmdline", "r") as f:
            contenido = f.read()
            comando = contenido.replace('\x00', ' ').strip()
            print(f"Comando: {comando if comando else '[vacío]'}")
    except Exception as e:
        print(f"Error leyendo cmdline: {e}")

    # 📌 2. status (estado y más info)
    try:
        print("\n--- Status ---")
        with open(f"{base}/status", "r") as f:
            for linea in f:
                if linea.startswith(("Name", "State", "Pid", "PPid", "VmSize")):
                    print(linea.strip())
    except Exception as e:
        print(f"Error leyendo status: {e}")

    # 📌 3. file descriptors
    try:
        fd_path = f"{base}/fd"
        fds = os.listdir(fd_path)

        print(f"\n--- File Descriptors ({len(fds)}) ---")

        for fd in fds[:10]:  # mostrar solo algunos
            try:
                target = os.readlink(f"{fd_path}/{fd}")
                print(f"{fd} -> {target}")
            except:
                print(f"{fd} -> [no accesible]")
    except Exception as e:
        print(f"Error leyendo fd: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} <PID>")
        sys.exit(1)

    pid = sys.argv[1]
    info_proceso(pid)