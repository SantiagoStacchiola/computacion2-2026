#!/usr/bin/env python3
"""Monitor de datos en un pipe."""
import sys

def main():
    bytes_total = 0
    lineas_total = 0

    for linea in sys.stdin:
        data = linea.encode()

        bytes_total += len(data)
        lineas_total += 1

        # reenviar al siguiente proceso
        sys.stdout.write(linea)

    sys.stdout.flush()

    # imprimir estadísticas a stderr (IMPORTANTE)
    print(
        f"\n[Monitor] Procesados {bytes_total} bytes, {lineas_total} líneas",
        file=sys.stderr
    )


if __name__ == "__main__":
    main()