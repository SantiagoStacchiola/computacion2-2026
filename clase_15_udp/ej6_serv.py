import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('localhost', 9999))

print("Esperando...")

while True:
    datos, origen = s.recvfrom(65535)
    print(f"Recibidos {len(datos)} bytes")