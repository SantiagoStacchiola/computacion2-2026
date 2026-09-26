#!/usr/bin/env python3

import socketserver
import socket
import sys
import threading
import time


class Handler(socketserver.StreamRequestHandler):


    def setup(self):
        super().setup()

        # Estado propio de ESTA conexión.
        self.nick = None

        with self.server.lock:
            self.server.conexiones += 1
            self.server.activos.add(self.client_address)

            # Necesitamos guardar el handler para poder
            # escribirle desde otro cliente.
            self.server.clientes.add(self)

    def finish(self):
        with self.server.lock:
            self.server.activos.discard(self.client_address)
            self.server.clientes.discard(self)

        super().finish()

    def responder(self, texto):
        self.wfile.write((texto + '\n').encode())
        self.wfile.flush()

    def broadcast(self, texto):
        """
        Envía texto a todos los clientes conectados.
        """

        # Copiamos la colección mientras tenemos el lock.
        with self.server.lock:
            clientes = list(self.server.clientes)

        # NO mantenemos el lock mientras hacemos I/O.
        for cliente in clientes:
            try:
                cliente.responder(texto)

            except (BrokenPipeError,
                    ConnectionResetError,
                    OSError):

                # Puede haberse desconectado justo
                # mientras intentábamos escribirle.
                with self.server.lock:
                    self.server.clientes.discard(cliente)
                    self.server.activos.discard(
                        cliente.client_address
                    )

    def handle(self):
        self.responder(
            'Servidor de comandos. Escribí AYUDA.'
        )

        try:
            for linea in self.rfile:

                partes = (
                    linea
                    .decode('utf-8', 'replace')
                    .strip()
                    .split(maxsplit=1)
                )

                if not partes:
                    continue

                cmd = partes[0].upper()

                resto = (
                    partes[1]
                    if len(partes) > 1
                    else ''
                )

                if cmd == 'TIME':
                    self.responder(
                        time.strftime(
                            '%Y-%m-%d %H:%M:%S'
                        )
                    )

                elif cmd == 'ECHO':
                    self.responder(resto)

                elif cmd == 'NICK':

                    if not resto:
                        self.responder(
                            'Uso: NICK <nombre>'
                        )
                    else:
                        self.nick = resto

                        self.responder(
                            f'Ahora sos {self.nick}'
                        )

                elif cmd == 'BROADCAST':

                    if not resto:
                        self.responder(
                            'Uso: BROADCAST <texto>'
                        )

                    else:
                        nombre = (
                            self.nick
                            if self.nick
                            else f'{self.client_address[0]}:'
                                 f'{self.client_address[1]}'
                        )

                        self.broadcast(
                            f'[{nombre}] {resto}'
                        )

                elif cmd == 'QUIEN':

                    with self.server.lock:
                        activos = sorted(
                            f'{h}:{p}'
                            for h, p
                            in self.server.activos
                        )

                    self.responder(
                        f'{len(activos)} conectados: '
                        + ', '.join(activos)
                    )

                elif cmd == 'CONTADOR':

                    with self.server.lock:
                        n = self.server.conexiones

                    self.responder(
                        'Conexiones totales '
                        f'desde el arranque: {n}'
                    )

                elif cmd == 'AYUDA':

                    self.responder(
                        'TIME | ECHO <texto> | '
                        'NICK <nombre> | '
                        'BROADCAST <texto> | '
                        'QUIEN | CONTADOR | '
                        'AYUDA | QUIT'
                    )

                elif cmd == 'QUIT':
                    self.responder('Chau')
                    return

                else:
                    self.responder(
                        f'Comando desconocido: {cmd}'
                    )

        except socket.timeout:
            self.responder(
                'Desconectado por inactividad'
            )

    def handle_error(self, *args):
        print(
            f'Error atendiendo a '
            f'{self.client_address}'
        )


class Servidor(socketserver.ThreadingTCPServer):

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.conexiones = 0
        self.activos = set()

        # NUEVO:
        # guardamos los handlers de los clientes
        # para poder escribirles.
        self.clientes = set()

        self.lock = threading.Lock()


if __name__ == '__main__':

    puerto = (
        int(sys.argv[1])
        if len(sys.argv) > 1
        else 8080
    )

    with Servidor(
        ('0.0.0.0', puerto),
        Handler
    ) as srv:

        print(
            f'Escuchando en 0.0.0.0:{puerto}'
        )

        print(
            'Probá: nc localhost',
            puerto
        )

        try:
            srv.serve_forever()

        except KeyboardInterrupt:
            print('\nServidor detenido')