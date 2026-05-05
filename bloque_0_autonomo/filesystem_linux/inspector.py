import argparse
import os
import stat
import pwd
import grp
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser(description="Inspector de archivos")
parser.add_argument("ruta")

args = parser.parse_args()
path = Path(args.ruta)

if not path.exists() and not path.is_symlink():
    print("Error: archivo no existe")
    exit()

info = os.lstat(path)

# tipo
if stat.S_ISREG(info.st_mode):
    tipo = "archivo regular"
elif stat.S_ISDIR(info.st_mode):
    tipo = "directorio"
elif stat.S_ISLNK(info.st_mode):
    tipo = "enlace simbólico"
elif stat.S_ISCHR(info.st_mode):
    tipo = "dispositivo de caracteres"
else:
    tipo = "otro"

# permisos
permisos = stat.filemode(info.st_mode)
octal = oct(info.st_mode)[-3:]

# usuario y grupo
usuario = pwd.getpwuid(info.st_uid).pw_name
grupo = grp.getgrgid(info.st_gid).gr_name

print(f"Archivo: {path}")
print(f"Tipo: {tipo}")

if path.is_symlink():
    destino = os.readlink(path)
    print(f"-> {destino}")

print(f"Tamaño: {info.st_size} bytes")
print(f"Permisos: {permisos} ({octal})")
print(f"Propietario: {usuario} (uid: {info.st_uid})")
print(f"Grupo: {grupo} (gid: {info.st_gid})")
print(f"Inodo: {info.st_ino}")
print(f"Enlaces duros: {info.st_nlink}")

print("Creación:", datetime.fromtimestamp(info.st_ctime))
print("Modificación:", datetime.fromtimestamp(info.st_mtime))
print("Acceso:", datetime.fromtimestamp(info.st_atime))

if path.is_dir():
    cantidad = len(list(path.iterdir()))
    print(f"Contenido: {cantidad} elementos")