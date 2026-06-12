#!/usr/bin/env python3
"""Buscar y reemplazar una palabra en archivo mapeado con mmap."""
import mmap
import os

# 1. Crear archivo con 5 líneas
archivo = "/tmp/tarea_mmap.txt"
with open(archivo, "wb") as f:
    f.write(b"Python es un lenguaje poderoso\n")
    f.write(b"Computacion II es excelente\n")
    f.write(b"El mmap permite acceso rapido\n")
    f.write(b"Linux es importante para sistemas\n")
    f.write(b"Los pipes conectan procesos\n")

print("=== Archivo original (cat) ===")
os.system(f"cat {archivo}")

# 2. Mapear y buscar/reemplazar
with open(archivo, "r+b") as f:
    with mmap.mmap(f.fileno(), 0) as mm:
        # Buscar palabra: "Python"
        palabra_buscar = b"Python"
        palabra_nueva = b"CSharp"  # Mismo largo (6 caracteres)
        
        pos = mm.find(palabra_buscar)
        if pos != -1:
            print(f"\n✓ Encontrado '{palabra_buscar.decode()}' en posición {pos}")
            mm.seek(pos)
            mm.write(palabra_nueva)
            print(f"✓ Reemplazado por '{palabra_nueva.decode()}'")
        else:
            print(f"✗ No se encontró '{palabra_buscar.decode()}'")

print("\n=== Archivo modificado (cat) ===")
os.system(f"cat {archivo}")