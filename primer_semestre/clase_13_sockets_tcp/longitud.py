#!/usr/bin/env python3

import socket
import struct


def recibir_exacto(sock, n):
    """Lee EXACTAMENTE n bytes, o None si cerraron antes."""
    datos = b''

    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))

        if not pedazo:
            return None

        datos += pedazo

    return datos


def enviar_mensaje(sock, payload: bytes):
    """Envía un mensaje con prefijo de longitud de 4 bytes."""
    cabecera = struct.pack('!I', len(payload))
    sock.sendall(cabecera + payload)


def recibir_mensaje(sock):
    """Recibe un mensaje con prefijo de longitud de 4 bytes."""
    cabecera = recibir_exacto(sock, 4)

    if cabecera is None:
        return None

    longitud = struct.unpack('!I', cabecera)[0]

    return recibir_exacto(sock, longitud)


def main():
    HOST = 'localhost'
    PORT = 8080

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen(1)

        print(f"Servidor escuchando en {HOST}:{PORT}")

        while True:
            conn, addr = servidor.accept()

            with conn:
                print(f"Cliente conectado: {addr}")

                while True:
                    mensaje = recibir_mensaje(conn)

                    if mensaje is None:
                        print("Cliente desconectado")
                        break

                    print(f"Recibido: {mensaje}")

                    respuesta = mensaje.upper()
                    enviar_mensaje(conn, respuesta)


if __name__ == '__main__':
    main()