import socket
import sys
import time

HOST = '0.0.0.0'
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


def atender(conn, direccion):
    """Devuelve todo lo que el cliente mande, hasta que cierre."""
    
    # Simula trabajo pesado durante 10 segundos.
    print(f'  [{direccion[0]}:{direccion[1]}] atendiendo...')
    time.sleep(10)

    total = 0

    while True:
        datos = conn.recv(4096)

        if not datos:
            # recv() vacío = el otro lado cerró.
            break

        total += len(datos)

        print(
            f'  [{direccion[0]}:{direccion[1]}] '
            f'recv {len(datos)} bytes: {datos!r}'
        )

        conn.sendall(datos)

    print(
        f'  [{direccion[0]}:{direccion[1]}] '
        f'cerró tras {total} bytes'
    )


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:

        servidor.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        servidor.bind((HOST, PUERTO))

        # Cola de conexiones pendientes.
        servidor.listen(5)

        print(
            f'Escuchando en {HOST}:{PUERTO} '
            f'(Ctrl+C para salir)'
        )

        while True:
            # accept() devuelve un socket NUEVO para ese cliente.
            conn, direccion = servidor.accept()

            print(f'Conexión desde {direccion}')

            try:
                with conn:
                    atender(conn, direccion)

            except (ConnectionResetError, BrokenPipeError) as e:
                # Una desconexión abrupta del cliente
                # no debe detener todo el servidor.
                print(
                    f'  [{direccion}] '
                    f'desconexión abrupta: {e}'
                )


if __name__ == '__main__':
    try:
        main()

    except KeyboardInterrupt:
        print('\nServidor detenido')