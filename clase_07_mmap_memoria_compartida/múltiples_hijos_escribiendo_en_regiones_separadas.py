#!/usr/bin/env python3
"""Varios hijos calculan suma de rangos en regiones separadas del mmap."""
import mmap
import os
import struct

NUM_HIJOS = 4
TAMAÑO_POR_HIJO = 64
TAMAÑO_TOTAL = NUM_HIJOS * TAMAÑO_POR_HIJO

# Rango total de números a sumar
INICIO = 1
FIN = 100
RANGO_POR_HIJO = (FIN - INICIO + 1) // NUM_HIJOS

mm = mmap.mmap(-1, TAMAÑO_TOTAL)

hijos = []
for i in range(NUM_HIJOS):
    pid = os.fork()
    if pid == 0:
        # Hijo: calcula suma de su rango
        offset = i * TAMAÑO_POR_HIJO

        # Calcular rango para este hijo
        inicio_rango = INICIO + i * RANGO_POR_HIJO
        fin_rango = inicio_rango + RANGO_POR_HIJO - 1

        # Calcular suma
        suma = sum(range(inicio_rango, fin_rango + 1))

        # Escribir ID del hijo
        struct.pack_into('i', mm, offset, i)

        # Escribir PID del hijo
        struct.pack_into('i', mm, offset + 4, os.getpid())

        # Escribir inicio del rango
        struct.pack_into('i', mm, offset + 8, inicio_rango)

        # Escribir fin del rango
        struct.pack_into('i', mm, offset + 12, fin_rango)

        # Escribir suma
        struct.pack_into('i', mm, offset + 16, suma)

        # Escribir mensaje
        msg = f"Suma de {inicio_rango}-{fin_rango}: {suma}".encode()
        mm[offset+20:offset+20+len(msg)] = msg

        os._exit(0)
    else:
        hijos.append(pid)

# Padre espera a todos
for pid in hijos:
    os.waitpid(pid, 0)

# Leer resultados y calcular total
print("=== Resultados de cada hijo ===")
suma_total = 0
for i in range(NUM_HIJOS):
    offset = i * TAMAÑO_POR_HIJO
    hijo_id = struct.unpack_from('i', mm, offset)[0]
    hijo_pid = struct.unpack_from('i', mm, offset + 4)[0]
    inicio_rango = struct.unpack_from('i', mm, offset + 8)[0]
    fin_rango = struct.unpack_from('i', mm, offset + 12)[0]
    suma = struct.unpack_from('i', mm, offset + 16)[0]
    msg = bytes(mm[offset+20:offset+TAMAÑO_POR_HIJO]).rstrip(b'\x00').decode()
    
    print(f"  Hijo {hijo_id} (PID {hijo_pid}): {msg}")
    suma_total += suma

print(f"\n✓ Suma total: {suma_total}")
print(f"✓ Verificación: suma de {INICIO}-{FIN} = {sum(range(INICIO, FIN+1))}")

mm.close()