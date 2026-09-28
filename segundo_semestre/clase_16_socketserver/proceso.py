import socketserver
import multiprocessing
import os


class Handler(socketserver.BaseRequestHandler):

    def handle(self):

        with self.server.contador.get_lock():
            self.server.contador.value += 1
            valor = self.server.contador.value

        print(
            "PID:",
            os.getpid(),
            "contador:",
            valor
        )


class Servidor(socketserver.ForkingTCPServer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.contador = multiprocessing.Value("i", 0)


with Servidor(("localhost", 8080), Handler) as server:

    print("Servidor iniciado")

    server.serve_forever()