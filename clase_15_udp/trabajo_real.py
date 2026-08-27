import socket

HOST = "127.0.0.1"
PUERTO = 5000

contador_trabajo = 0

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind((HOST, PUERTO))

    print(f"Servidor escuchando en {HOST}:{PUERTO}")

    while True:
        mensaje, direccion = sock.recvfrom(65535)

        print(f"Pedido recibido: {mensaje.decode()}")

        # TRABAJO REAL
        contador_trabajo += 1

        print(f"Trabajo ejecutado {contador_trabajo} vez/veces")

        # Responder
        sock.sendto(mensaje.upper(), direccion)