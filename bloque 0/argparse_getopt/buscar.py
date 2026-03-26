import argparse
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description="Mini grep en Python")

parser.add_argument("patron", help="Patrón a buscar")
parser.add_argument("archivos", nargs="*", help="Archivos a procesar")

parser.add_argument("-i", "--ignore-case", action="store_true")
parser.add_argument("-n", "--line-number", action="store_true")
parser.add_argument("-c", "--count", action="store_true")
parser.add_argument("-v", "--invert", action="store_true")

args = parser.parse_args()

patron = args.patron
if args.ignore_case:
    patron = patron.lower()

def procesar_lineas(lineas, nombre_archivo=None):
    coincidencias = 0

    for i, linea in enumerate(lineas, 1):
        texto = linea.rstrip("\n")
        comparar = texto.lower() if args.ignore_case else texto

        match = patron in comparar

        if args.invert:
            match = not match

        if match:
            coincidencias += 1

            if not args.count:
                prefix = ""
                if nombre_archivo:
                     prefix += f"{nombre_archivo}:"

                if args.line_number or args.archivos:
                    prefix += f"{i}:"

                print(prefix + texto)

    return coincidencias


total = 0

# stdin
if not args.archivos and not sys.stdin.isatty():
    total += procesar_lineas(sys.stdin)
else:
    for archivo in args.archivos:
        try:
            with open(archivo, encoding="utf-8") as f:
                c = procesar_lineas(f, archivo)
                total += c

                if args.count:
                    print(f"{archivo}: {c} coincidencias")

        except Exception:
            print(f"Error leyendo '{archivo}'")

if args.count and len(args.archivos) > 1:
    print(f"Total: {total} coincidencias")