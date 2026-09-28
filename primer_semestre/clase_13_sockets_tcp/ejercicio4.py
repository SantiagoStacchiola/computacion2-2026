import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
mensaje = 'hola'
s.sendall(mensaje.encode('utf-8'))