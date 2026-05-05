import argparse
from pathlib import Path
import fnmatch

parser = argparse.ArgumentParser(description="Uso de disco")
parser.add_argument("directorio")
parser.add_argument("--depth", type=int, default=1)
parser.add_argument("--top", type=int)
parser.add_argument("--exclude")

args = parser.parse_args()

ruta = Path(args.directorio)

patterns = args.exclude.split(",") if args.exclude else []

def excluido(p):
    return any(fnmatch.fnmatch(p.name, pat) for pat in patterns)

def size_dir(path, depth):
    # 📌 si es archivo → devolver tamaño directo
    if path.is_file():
        return path.stat().st_size

    # 📌 si no es directorio → ignorar
    if not path.is_dir():
        return 0

    total = 0

    if depth < 0:
        return 0

    for item in path.iterdir():
        if excluido(item):
            continue

        total += size_dir(item, depth - 1)

    return total

resultados = []

for item in ruta.iterdir():
    if excluido(item):
        continue
    s = size_dir(item, args.depth)
    resultados.append((item, s))

resultados.sort(key=lambda x: x[1], reverse=True)

if args.top:
    resultados = resultados[:args.top]

def human(size):
    for unit in ["B", "K", "M", "G"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024

total = 0

for p, s in resultados:
    print(f"{human(s):>8}  {p}")
    total += s

print("─" * 25)
print(f"Total: {human(total)}")