#!/usr/bin/env python3
"""Versión simplificada de pstree."""

import os

def obtener_procesos():
    """Devuelve diccionario PID -> PPID."""
    procesos = {}

    for entrada in os.listdir("/proc"):
        if entrada.isdigit():
            pid = int(entrada)
            try:
                with open(f"/proc/{pid}/status") as f:
                    ppid = None
                    nombre = None

                    for linea in f:
                        if linea.startswith("Name:"):
                            nombre = linea.split()[1]
                        elif linea.startswith("PPid:"):
                            ppid = int(linea.split()[1])
                            break

                    if ppid is not None:
                        procesos[pid] = (ppid, nombre)

            except:
                continue

    return procesos


def construir_arbol(procesos):
    """Construye PPID -> [hijos]."""
    arbol = {}

    for pid, (ppid, _) in procesos.items():
        arbol.setdefault(ppid, []).append(pid)

    return arbol


def imprimir_arbol(pid, procesos, arbol, nivel=0):
    """Imprime recursivamente el árbol."""
    if pid not in procesos:
        return

    _, nombre = procesos[pid]
    print("  " * nivel + f"{nombre} ({pid})")

    for hijo in sorted(arbol.get(pid, [])):
        imprimir_arbol(hijo, procesos, arbol, nivel + 1)


def main():
    procesos = obtener_procesos()
    arbol = construir_arbol(procesos)

    print("Árbol de procesos:\n")

    # PID 1 suele ser el root (init/systemd)
    raiz = 1

    imprimir_arbol(raiz, procesos, arbol)


if __name__ == "__main__":
    main()
