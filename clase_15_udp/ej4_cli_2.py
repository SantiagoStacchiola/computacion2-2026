import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(('localhost', 6000))

input("Presioná ENTER para enviar al servidor...")

s.sendto(b"Hola desde el puerto 6000", ('localhost', 9999))

print("Mensaje enviado")