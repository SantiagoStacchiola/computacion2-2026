import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Buscar archivos grandes")

parser.add_argument("directorio")
parser.add_argument("--min-size", required=True, help="Ej: 100K, 1M, 2G")
parser.add_argument("--type", choices=["f", "d"])
parser.add_argument("--top", type=int)

args = parser.parse_args()

# 🔹 convertir tamaño a bytes
def parse_size(s):
    unidades = {"K": 1024, "M": 1024**2, "G": 1024**3}
    if s[-1].upper() in unidades:
        return int(float(s[:-1]) * unidades[s[-1].upper()])
    return int(s)

min_size = parse_size(args.min_size)

ruta = Path(args.directorio)

resultados = []

# 🔹 recorrer recursivamente
for item in ruta.rglob("*"):
    try:
        if args.type == "f" and not item.is_file():
            continue
        if args.type == "d" and not item.is_dir():
            continue

        size = item.stat().st_size

        if size >= min_size:
            resultados.append((item, size))

    except Exception:
        continue

# 🔹 ordenar por tamaño
resultados.sort(key=lambda x: x[1], reverse=True)

# 🔹 top
if args.top:
    resultados = resultados[:args.top]

# 🔹 formato legible
def human(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024

# 🔹 mostrar
total_size = 0

for path, size in resultados:
    print(f"{path} ({human(size)})")
    total_size += size

print(f"Total: {len(resultados)} archivos, {human(total_size)}")