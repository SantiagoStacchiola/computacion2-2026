import argparse
import os
from pathlib import Path

parser = argparse.ArgumentParser(description="Detectar enlaces rotos")

parser.add_argument("directorio")
parser.add_argument("--delete", action="store_true")
parser.add_argument("--quiet", action="store_true")

args = parser.parse_args()

ruta = Path(args.directorio)

rotos = []

for item in ruta.rglob("*"):
    try:
        if item.is_symlink() and not item.exists():
            rotos.append(item)
    except Exception:
        continue

# 🔹 modo quiet
if args.quiet:
    print(len(rotos))
    exit()

print(f"Buscando enlaces simbólicos rotos en {ruta}...\n")

if not rotos:
    print("No se encontraron enlaces rotos")
    exit()

print("Enlaces rotos encontrados:")

for link in rotos:
    destino = os.readlink(link)
    print(f"  {link} -> {destino} (no existe)")

print(f"\nTotal: {len(rotos)} enlaces rotos")

# 🔹 eliminar
if args.delete:
    for link in rotos:
        confirm = input(f"¿Eliminar {link}? [s/N] ")
        if confirm.lower() == "s":
            link.unlink()
            print("Eliminado")