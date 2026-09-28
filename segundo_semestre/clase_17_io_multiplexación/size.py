import select
import socket

relleno = [socket.socket() for _ in range(1100)]

alto = relleno[-1]

print("fd:", alto.fileno())

select.select([alto], [], [], 0)