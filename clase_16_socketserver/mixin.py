import socketserver
import time


class Eco(socketserver.BaseRequestHandler):

    def handle(self):
        print("Cliente conectado")

        time.sleep(5)

        datos = self.request.recv(1024)

        if datos:
            self.request.sendall(datos.upper())

        print("Cliente terminado")


class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    pass


print("MRO de Bien:")
for clase in Bien.mro():
    print("  ", clase)

print()

print("MRO de Mal:")
for clase in Mal.mro():
    print("  ", clase)