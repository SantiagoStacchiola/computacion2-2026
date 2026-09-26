#!/usr/bin/env python3

import socketserver
import threading
import time
import os


class Contador(socketserver.StreamRequestHandler):
    def handle(self):
        with self.server.lock:
            self.server.visitas += 1
            n = self.server.visitas
        self.wfile.write(
            f'visita {n}\n'.encode()
        )
        

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visitas = 0
        self.lock = threading.Lock()


Servidor(("localhost", 8080), Contador).serve_forever()