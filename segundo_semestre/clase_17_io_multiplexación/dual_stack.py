import socket

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

s.setsockopt(
    socket.IPPROTO_IPV6,
    socket.IPV6_V6ONLY,
    0
)

s.bind(('::', 8080))
s.listen(5)

print("Servidor escuchando...")