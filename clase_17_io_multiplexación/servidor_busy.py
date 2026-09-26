#!/usr/bin/env python3

import socket

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

srv.bind(('localhost', 8080))
srv.listen(5)

srv.setblocking(False)

conexiones = []

while True:

    # Intentar aceptar nuevos clientes
    try:
        conn, direccion = srv.accept()
        conn.setblocking(False)
        conexiones.append(conn)

        print(f"Nuevo cliente: {direccion}")

    except BlockingIOError:
        pass

    # Revisar clientes existentes
    for c in list(conexiones):

        try:
            datos = c.recv(4096)

            if datos:
                c.sendall(datos)

            else:
                conexiones.remove(c)
                c.close()

        except BlockingIOError:
            pass