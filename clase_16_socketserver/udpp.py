import socketserver
import time


class Handler(socketserver.DatagramRequestHandler):
    def handle(self):
        print("Procesando...")

        time.sleep(5)

        datos = self.rfile.read()
        self.wfile.write(datos.upper())


with socketserver.ThreadingUDPServer(
    ("localhost", 8080),
    Handler
) as server:
    server.serve_forever()