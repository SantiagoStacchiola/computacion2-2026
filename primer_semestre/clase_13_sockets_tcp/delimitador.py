#!/usr/bin/env python3
"""Servidor con framing por líneas."""
import socket


def recibir_lineas(sock):
    """Generador de líneas completas."""
    buffer = b''

    while True:
        pedazo = sock.recv(4096)

        if not pedazo:
            return

        buffer += pedazo

        while b'\n' in buffer:
            linea, buffer = buffer.split(b'\n', 1)
            yield linea


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

                for linea in recibir_lineas(conn):
                    respuesta = linea.upper() + b'\n'
                    conn.sendall(respuesta)


if __name__ == '__main__':
    main()