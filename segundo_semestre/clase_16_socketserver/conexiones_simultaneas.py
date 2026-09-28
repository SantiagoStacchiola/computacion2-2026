#!/usr/bin/env python3

import socket
import time


HOST = 'localhost'
PUERTO = 8080
CANTIDAD = 1000

sockets = []


for i in range(CANTIDAD):
    try:
        sock = socket.create_connection((HOST, PUERTO))
        sockets.append(sock)

        print(f'Conexión {i + 1} abierta')

    except OSError as e:
        print(f'Error en conexión {i + 1}: {e}')
        break


print()
print(f'Total abiertas: {len(sockets)}')
print('Las conexiones quedan abiertas.')
print('Ctrl+C para cerrarlas.')


try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print('\nCerrando conexiones...')

finally:
    for sock in sockets:
        sock.close()