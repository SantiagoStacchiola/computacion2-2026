import socketserver
import time


class Handler(socketserver.BaseRequestHandler):

    def handle(self):
        print("Cliente conectado")

        while True:
            time.sleep(1)


class Servidor(socketserver.ThreadingMixIn,
               socketserver.TCPServer):
    
    allow_reuse_address = True
    daemon_threads = True


with Servidor(("localhost", 8080), Handler) as server:

    print("Servidor iniciado")

    server.serve_forever()