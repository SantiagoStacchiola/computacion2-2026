import socket

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

s.bind(('::1', 0))

print(s.getsockname())

info = s.getsockname()

host = info[0]
puerto = info[1]

print(host)
print(puerto)