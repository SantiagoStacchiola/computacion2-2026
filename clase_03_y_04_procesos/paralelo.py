#!/usr/bin/env python3
"""
Ejecutor de comandos en paralelo.
Uso: python3 paralelo.py "cmd1" "cmd2" ...
"""
import os
import sys
import time

def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} comando1 [comando2 ...]")
        sys.exit(1)

    comandos = sys.argv[1:]
    inicio = time.time()

    procesos = {}  # PID -> comando

    #Lanzar todos los procesos
    for cmd in comandos:
        partes = cmd.split()

        pid = os.fork()

        if pid == 0:
            # HIJO
            try:
                os.execvp(partes[0], partes)
            except OSError as e:
                print(f"Error ejecutando {cmd}: {e}")
                os._exit(127)
        else:
            # PADRE
            procesos[pid] = cmd
            print(f"[{pid}] Iniciado: {cmd}")

    #Esperar a todos
    resultados = []

    while procesos:
        pid, status = os.wait()
        codigo = os.WEXITSTATUS(status)

        cmd = procesos.pop(pid)
        print(f"[{pid}] Terminado: {cmd} (código: {codigo})")

        resultados.append(codigo)

    duracion = time.time() - inicio

    #Resumen
    exitosos = sum(1 for c in resultados if c == 0)

    print("\nResumen:")
    print(f"- Comandos ejecutados: {len(comandos)}")
    print(f"- Exitosos: {exitosos}")
    print(f"- Fallidos: {len(comandos) - exitosos}")
    print(f"- Tiempo total: {duracion:.2f}s")


if __name__ == "__main__":
    main()