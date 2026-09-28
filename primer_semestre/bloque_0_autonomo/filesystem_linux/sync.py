import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description="Sincronizador simple")
parser.add_argument("origen")
parser.add_argument("destino")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--delete", action="store_true")

args = parser.parse_args()

src = Path(args.origen)
dst = Path(args.destino)

def listar(base):
    return {p.relative_to(base): p for p in base.rglob("*") if p.is_file()}

src_files = listar(src)
dst_files = listar(dst)

nuevos = []
modificados = []
eliminados = []

for f in src_files:
    if f not in dst_files:
        nuevos.append(f)
    else:
        s1 = src_files[f].stat()
        s2 = dst_files[f].stat()
        if s1.st_mtime > s2.st_mtime:
            modificados.append(f)

for f in dst_files:
    if f not in src_files:
        eliminados.append(f)

print("Cambios detectados:\n")

for f in nuevos:
    print(f"NUEVO: {f}")

for f in modificados:
    print(f"MODIFICADO: {f}")

for f in eliminados:
    print(f"ELIMINADO: {f}")

if args.dry_run:
    exit()

confirm = input("\n¿Proceder? [s/N] ")
if confirm.lower() != "s":
    exit()

# copiar
for f in nuevos + modificados:
    origen_path = src / f
    destino_path = dst / f
    destino_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen_path, destino_path)
    print(f"Copiado {f}")

# eliminar
if args.delete:
    for f in eliminados:
        (dst / f).unlink()
        print(f"Eliminado {f}")