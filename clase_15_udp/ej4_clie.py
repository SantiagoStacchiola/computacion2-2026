import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.connect(('localhost', 9999))

s.send(b'hola')

try:
    respuesta = s.recv(4096)
    print("Recibido:", respuesta)
except TimeoutError:
    print("timeout")