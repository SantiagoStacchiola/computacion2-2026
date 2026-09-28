import socket


def pedir_con_reintentos(sock, mensaje, destino, intentos=5, timeout=0.5):
    """Manda un mensaje y reintenta si no llega respuesta."""

    sock.settimeout(timeout)

    for intento in range(1, intentos + 1):
        print(f"Intento {intento}/{intentos}")

        sock.sendto(mensaje, destino)

        try:
            respuesta, _ = sock.recvfrom(65535)
            print("Respuesta recibida.")
            return respuesta

        except TimeoutError:
            print("Timeout: no llegó respuesta.")

    print("Se agotaron los intentos.")
    return None


# Dirección del servidor
HOST = "127.0.0.1"
PUERTO = 5000

# Crear socket UDP
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

    mensaje = input("Ingrese un mensaje: ").encode()

    respuesta = pedir_con_reintentos(
        sock,
        mensaje,
        (HOST, PUERTO),
        intentos=5,
        timeout=0.5
    )

    if respuesta is not None:
        print("Respuesta del servidor:", respuesta.decode())
    else:
        print("No se recibió respuesta.")