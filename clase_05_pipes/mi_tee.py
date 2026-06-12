#!/usr/bin/env python3
"""Implementación simple de tee."""
import sys

def main():
    if len(sys.argv) != 2:
        print(f"Uso: {sys.argv[0]} archivo", file=sys.stderr)
        sys.exit(1)

    archivo = sys.argv[1]

    try:
        with open(archivo, "w") as f:
            for linea in sys.stdin:
                # escribir en archivo
                f.write(linea)
                f.flush()

                # escribir en stdout
                sys.stdout.write(linea)
                sys.stdout.flush()

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()