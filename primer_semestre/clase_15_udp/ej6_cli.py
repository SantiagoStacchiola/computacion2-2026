import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

datos = b'A' * 60000

s.sendto(datos, ('localhost', 9999))

print("Datagrama enviado")