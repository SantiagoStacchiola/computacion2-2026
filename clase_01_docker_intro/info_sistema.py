#!/usr/bin/env python3

import sys
import os
import platform

print("="*50)
print("INFORMACIÓN DEL SISTEMA")
print("="*50)

# 🐍 Python
print(f"Versión de Python:\n{sys.version}\n")

# 🖥 Sistema operativo
print(f"Sistema operativo:")
print(f"  Nombre: {platform.system()}")
print(f"  Versión: {platform.version()}")
print(f"  Release: {platform.release()}\n")

# 🧠 CPUs
print(f"CPUs disponibles: {os.cpu_count()}\n")

# 💾 Memoria (Linux)
try:
    with open("/proc/meminfo") as f:
        meminfo = f.read()

    total = [line for line in meminfo.split("\n") if "MemTotal" in line][0]
    print(f"Memoria total: {total}\n")
except:
    print("Memoria: No disponible\n")

# 🌱 Variables de entorno
print("Variables de entorno (PYTHON*):")
for k, v in os.environ.items():
    if k.startswith("PYTHON"):
        print(f"  {k}={v}")

print("="*50)