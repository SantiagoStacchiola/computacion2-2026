import socket
import struct


def recibir_exacto(sock, n):
    datos = b''

    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))

        if not pedazo:
            return None

        datos += pedazo

    return datos


def enviar_mensaje(sock, payload):
    cabecera = struct.pack('!I', len(payload))
    sock.sendall(cabecera + payload)


def recibir_mensaje(sock):
    cabecera = recibir_exacto(sock, 4)

    if cabecera is None:
        return None

    longitud = struct.unpack('!I', cabecera)[0]

    return recibir_exacto(sock, longitud)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('localhost', 8080))

    enviar_mensaje(s, b'uno')
    print(recibir_mensaje(s))

    enviar_mensaje(s, b'dos')
    print(recibir_mensaje(s))

    enviar_mensaje(s, b'tres\ncuatro')
    print(recibir_mensaje(s))