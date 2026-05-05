import argparse
from pathlib import Path
import hashlib

parser = argparse.ArgumentParser(description="Comparador de directorios")
parser.add_argument("dir1")
parser.add_argument("dir2")
parser.add_argument("--recursive", action="store_true")
parser.add_argument("--checksum", action="store_true")

args = parser.parse_args()

d1 = Path(args.dir1)
d2 = Path(args.dir2)

def listar(ruta):
    if args.recursive:
        return {p.relative_to(ruta): p for p in ruta.rglob("*") if p.is_file()}
    else:
        return {p.name: p for p in ruta.iterdir() if p.is_file()}

files1 = listar(d1)
files2 = listar(d2)

solo1 = set(files1) - set(files2)
solo2 = set(files2) - set(files1)
comunes = set(files1) & set(files2)

mod_tamano = []
mod_fecha = []
identicos = 0

def hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

for f in comunes:
    p1 = files1[f]
    p2 = files2[f]

    s1 = p1.stat()
    s2 = p2.stat()

    if args.checksum:
        if hash_file(p1) != hash_file(p2):
            mod_tamano.append((f, s1.st_size, s2.st_size))
        else:
            identicos += 1
    else:
        if s1.st_size != s2.st_size:
            mod_tamano.append((f, s1.st_size, s2.st_size))
        elif s1.st_mtime != s2.st_mtime:
            mod_fecha.append((f, s1.st_mtime, s2.st_mtime))
        else:
            identicos += 1

print(f"Comparando {d1} con {d2}...\n")

print("Solo en dir1:")
for f in solo1:
    print(f"  {f}")

print("\nSolo en dir2:")
for f in solo2:
    print(f"  {f}")

print("\nModificados (tamaño diferente):")
for f, a, b in mod_tamano:
    print(f"  {f} ({a} -> {b} bytes)")

print("\nModificados (fecha diferente):")
for f, a, b in mod_fecha:
    print(f"  {f}")

print(f"\nIdénticos: {identicos} archivos")