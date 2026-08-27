import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

s.settimeout(2.0)

s.sendto(b'DISCOVER?', ('255.255.255.255', 8082))

try:
    datos, origen = s.recvfrom(4096)
    print(f'{origen} respondió: {datos!r}')
except TimeoutError:
    print('Nadie respondió')