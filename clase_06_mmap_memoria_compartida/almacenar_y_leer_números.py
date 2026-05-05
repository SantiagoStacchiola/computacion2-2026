#!/usr/bin/env python3
"""Usar mmap como almacenamiento binario estructurado con registros."""
import mmap
import struct
import os

ARCHIVO = "/tmp/registros.bin"
NUM_REGISTROS = 5
FORMATO = 'i f 20s'  # int (id) + float (nota) + 20 bytes (nombre)
TAMAÑO_REGISTRO = struct.calcsize(FORMATO)  # 4 + 4 + 20 = 28 bytes
TAMAÑO_TOTAL = NUM_REGISTROS * TAMAÑO_REGISTRO

# Crear archivo con tamaño fijo
with open(ARCHIVO, "wb") as f:
    f.write(b'\x00' * TAMAÑO_TOTAL)

with open(ARCHIVO, "r+b") as f:
    mm = mmap.mmap(f.fileno(), TAMAÑO_TOTAL)

    # Escribir registros
    print("Escribiendo registros...")
    registros = [
        (1, 8.5, b"Juan"),
        (2, 9.0, b"Maria"),
        (3, 7.5, b"Carlos"),
        (4, 8.8, b"Ana"),
        (5, 9.5, b"Roberto"),
    ]
    
    for i, (id_est, nota, nombre) in enumerate(registros):
        offset = i * TAMAÑO_REGISTRO
        struct.pack_into(FORMATO, mm, offset, id_est, nota, nombre)
        print(f"  Registro {i}: id={id_est}, nota={nota}, nombre={nombre.decode()}")

    # Leer todos los registros
    print("\nLeyendo registros...")
    for i in range(NUM_REGISTROS):
        offset = i * TAMAÑO_REGISTRO
        id_est, nota, nombre = struct.unpack_from(FORMATO, mm, offset)
        nombre = nombre.decode().strip('\x00')
        print(f"  Registro {i}: id={id_est}, nota={nota}, nombre={nombre}")

    # Modificar un registro (cambiar nota de registro 2)
    offset = 2 * TAMAÑO_REGISTRO
    struct.pack_into(FORMATO, mm, offset, 3, 10.0, b"Carlos_modificado")
    print(f"\nRegistro 2 modificado")

    print("\nDespués de modificar:")
    id_est, nota, nombre = struct.unpack_from(FORMATO, mm, offset)
    nombre = nombre.decode().strip('\x00')
    print(f"  Registro 2: id={id_est}, nota={nota}, nombre={nombre}")

    mm.close()

os.unlink(ARCHIVO)