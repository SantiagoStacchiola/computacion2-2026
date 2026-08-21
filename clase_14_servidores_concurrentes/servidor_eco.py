import socketserver

class EchoHandler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            data = self.rfile.readline()

            if not data:
                break

            self.wfile.write(data)

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Servidor(("localhost", 8080), EchoHandler) as server:
        print("Servidor escuchando en localhost:8080")
        server.serve_forever()