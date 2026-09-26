import select
import socket

relleno = [socket.socket() for _ in range(1100)]

alto = relleno[-1]

print("fd:", alto.fileno())

poller = select.poll()

poller.register(alto, select.POLLIN)

print(poller.poll(0))