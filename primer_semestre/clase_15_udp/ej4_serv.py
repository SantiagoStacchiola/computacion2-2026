import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('localhost', 9999))

while True:
    datos, direccion = s.recvfrom(4096)
    print("Recibido:", datos, "desde", direccion)