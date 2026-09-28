import argparse
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Lista archivos de un directorio"
)

# argumento opcional (default = actual)
parser.add_argument(
    "directorio",
    nargs="?",
    default=".",
    help="Directorio a listar"
)

# flags
parser.add_argument(
    "-a", "--all",
    action="store_true",
    help="Incluir archivos ocultos"
)

parser.add_argument(
    "--extension",
    help="Filtrar por extensión (ej: .py)"
)

args = parser.parse_args()

ruta = Path(args.directorio)

if not ruta.exists():
    print(f"Error: el directorio '{ruta}' no existe")
    exit()

for item in ruta.iterdir():
    nombre = item.name

    # ocultos
    if not args.all and nombre.startswith("."):
        continue

    # filtro por extensión
    if args.extension and item.is_file():
        if not nombre.endswith(args.extension):
            continue

    # agregar / a directorios
    if item.is_dir():
        print(nombre + "/")
    else:
        print(nombre)