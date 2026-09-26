#!/usr/bin/env python3
"""
Chat multiusuario con selectors.

Ejercicio 6 - Computación II

Características:
- Múltiples clientes simultáneos.
- Retransmisión de mensajes.
- /nick <nombre> para cambiar el apodo.
- /lista para ver los usuarios conectados.
- Framing mediante un buffer por cliente.
- Escritura no bloqueante mediante send() + EVENT_WRITE.
- Un solo hilo/event loop.
"""

import selectors
import socket
import sys


# ------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8083

sel = selectors.DefaultSelector()

# socket -> apodo
clientes = {}

# socket -> bytes pendientes de enviar
salida = {}

# socket -> bytes recibidos pero todavía no procesados
buffers = {}


# ------------------------------------------------------------
# DIFUSIÓN
# ------------------------------------------------------------

def difundir(mensaje: bytes, excepto=None):
    """
    Encola un mensaje para todos los clientes excepto 'excepto'.

    No se hace send() directamente porque un cliente lento podría
    bloquear al servidor. El mensaje queda en salida[] y el selector
    avisará cuando el socket pueda escribir.
    """

    for conn in list(clientes):

        if conn is excepto:
            continue

        salida[conn] = salida.get(conn, b'') + mensaje

        sel.modify(
            conn,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            manejar
        )


# ------------------------------------------------------------
# ACEPTAR CLIENTE
# ------------------------------------------------------------

def aceptar(servidor, _mascara):
    """
    Acepta una nueva conexión y la registra en el selector.
    """

    conn, direccion = servidor.accept()

    conn.setblocking(False)

    apodo = f'{direccion[0]}:{direccion[1]}'

    clientes[conn] = apodo

    # Buffer de entrada independiente para cada cliente.
    buffers[conn] = b''

    # Buffer de salida independiente para cada cliente.
    salida[conn] = (
        b'Bienvenido al chat.\n'
        b'Escribi un mensaje y presiona Enter.\n'
        b'Comandos disponibles:\n'
        b'  /nick <nombre>\n'
        b'  /lista\n'
    )

    sel.register(
        conn,
        selectors.EVENT_READ | selectors.EVENT_WRITE,
        manejar
    )

    print(f'+ {apodo}  ({len(clientes)} conectados)')

    difundir(
        f'* se conecto {apodo}\n'.encode(),
        excepto=conn
    )


# ------------------------------------------------------------
# DESCONEXIÓN
# ------------------------------------------------------------

def desconectar(conn):
    """
    Elimina un cliente y libera todos sus recursos.
    """

    apodo = clientes.pop(conn, '?')

    salida.pop(conn, None)
    buffers.pop(conn, None)

    # Siempre desregistramos antes de cerrar.
    try:
        sel.unregister(conn)
    except KeyError:
        pass

    conn.close()

    print(f'- {apodo}  ({len(clientes)} conectados)')

    difundir(
        f'* se fue {apodo}\n'.encode()
    )


# ------------------------------------------------------------
# CAMBIAR NICK
# ------------------------------------------------------------

def cambiar_nick(conn, nuevo_nick):
    """
    Cambia el apodo del cliente.
    """

    nuevo_nick = nuevo_nick.strip()

    if not nuevo_nick:
        salida[conn] = (
            salida.get(conn, b'') +
            b'Uso: /nick <nombre>\n'
        )

        sel.modify(
            conn,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            manejar
        )

        return

    # Evitamos que dos clientes tengan el mismo apodo.
    for otro_conn, otro_nick in clientes.items():

        if otro_conn is not conn and otro_nick == nuevo_nick:

            salida[conn] = (
                salida.get(conn, b'') +
                f'El apodo "{nuevo_nick}" ya esta en uso.\n'.encode()
            )

            sel.modify(
                conn,
                selectors.EVENT_READ | selectors.EVENT_WRITE,
                manejar
            )

            return

    viejo_nick = clientes[conn]

    clientes[conn] = nuevo_nick

    print(f'* {viejo_nick} ahora es {nuevo_nick}')

    difundir(
        f'* {viejo_nick} ahora es {nuevo_nick}\n'.encode()
    )


# ------------------------------------------------------------
# LISTA DE CLIENTES
# ------------------------------------------------------------

def mostrar_lista(conn):
    """
    Envía al cliente la lista de usuarios conectados.
    """

    nombres = list(clientes.values())

    mensaje = (
        f'Usuarios conectados ({len(nombres)}):\n'
    )

    for nombre in nombres:
        mensaje += f'  - {nombre}\n'

    salida[conn] = (
        salida.get(conn, b'') +
        mensaje.encode()
    )

    sel.modify(
        conn,
        selectors.EVENT_READ | selectors.EVENT_WRITE,
        manejar
    )


# ------------------------------------------------------------
# PROCESAR UNA LÍNEA
# ------------------------------------------------------------

def procesar_linea(conn, linea):
    """
    Procesa una línea completa recibida desde un cliente.
    """

    # Eliminamos espacios innecesarios.
    texto = linea.decode(
        'utf-8',
        errors='replace'
    ).strip()

    if not texto:
        return

    apodo = clientes.get(conn, '?')

    # --------------------------------------------------------
    # /nick
    # --------------------------------------------------------

    if texto.startswith('/nick'):

        partes = texto.split(maxsplit=1)

        if len(partes) == 1:
            salida[conn] = (
                salida.get(conn, b'') +
                b'Uso: /nick <nombre>\n'
            )

            sel.modify(
                conn,
                selectors.EVENT_READ | selectors.EVENT_WRITE,
                manejar
            )

            return

        nuevo_nick = partes[1]

        cambiar_nick(
            conn,
            nuevo_nick
        )

        return

    # --------------------------------------------------------
    # /lista
    # --------------------------------------------------------

    if texto == '/lista':

        mostrar_lista(conn)

        return

    # --------------------------------------------------------
    # MENSAJE NORMAL
    # --------------------------------------------------------

    print(f'  <{apodo}> {texto}')

    mensaje = f'<{apodo}> {texto}\n'.encode()

    difundir(
        mensaje,
        excepto=conn
    )


# ------------------------------------------------------------
# LECTURA
# ------------------------------------------------------------

def leer(conn):
    """
    Recibe datos y los agrega al buffer del cliente.

    TCP es un flujo de bytes: un recv() puede traer:
    - media línea
    - una línea
    - varias líneas

    Por eso NO procesamos directamente el recv().
    """

    try:
        datos = conn.recv(4096)

    except ConnectionResetError:
        desconectar(conn)
        return

    if not datos:
        desconectar(conn)
        return

    # Agregamos lo recibido al buffer correspondiente.
    buffers[conn] += datos

    # --------------------------------------------------------
    # FRAMING
    # --------------------------------------------------------
    #
    # Buscamos '\n'.
    #
    # Si encontramos una línea:
    #
    #     linea + resto
    #
    # procesamos la línea y conservamos el resto.
    #
    # Esto permite manejar correctamente:
    #
    #   "hola\n"
    #
    #   "ho"
    #   "la\n"
    #
    #   "hola\nchau\n"
    #
    # --------------------------------------------------------

    while b'\n' in buffers[conn]:

        linea, resto = buffers[conn].split(
            b'\n',
            1
        )

        buffers[conn] = resto

        procesar_linea(
            conn,
            linea
        )

        # Puede ocurrir que procesar_linea()
        # haya provocado una desconexión.
        if conn not in clientes:
            return


# ------------------------------------------------------------
# ESCRITURA
# ------------------------------------------------------------

def escribir(conn):
    """
    Envía los datos pendientes sin bloquear.

    Se usa send(), NO sendall().
    """

    buf = salida.get(conn, b'')

    if buf:

        try:
            n = conn.send(buf)

        except (
            BrokenPipeError,
            ConnectionResetError
        ):
            desconectar(conn)
            return

        # Eliminamos del buffer los bytes que ya fueron enviados.
        salida[conn] = buf[n:]

    # Si ya no queda nada pendiente, dejamos de vigilar
    # EVENT_WRITE.
    if (
        conn in clientes
        and not salida.get(conn)
    ):

        sel.modify(
            conn,
            selectors.EVENT_READ,
            manejar
        )


# ------------------------------------------------------------
# HANDLER
# ------------------------------------------------------------

def manejar(conn, mascara):
    """
    Handler principal.

    Puede recibir:
    - EVENT_READ
    - EVENT_WRITE
    - ambos simultáneamente
    """

    if mascara & selectors.EVENT_READ:

        leer(conn)

        # Si el cliente se desconectó durante la lectura,
        # no intentamos escribir sobre él.
        if conn not in clientes:
            return

    if mascara & selectors.EVENT_WRITE:

        escribir(conn)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor.bind(
        ('0.0.0.0', PUERTO)
    )

    servidor.listen(128)

    servidor.setblocking(False)

    sel.register(
        servidor,
        selectors.EVENT_READ,
        aceptar
    )

    print(
        f'Chat escuchando en 0.0.0.0:{PUERTO} '
        f'({type(sel).__name__})'
    )

    print(
        'Conectate con: nc localhost',
        PUERTO
    )

    try:

        while True:

            eventos = sel.select()

            for clave, mascara in eventos:

                callback = clave.data

                callback(
                    clave.fileobj,
                    mascara
                )

    except KeyboardInterrupt:

        print('\nChat detenido')

    finally:

        # Cerramos los clientes.
        for conn in list(clientes):

            try:
                sel.unregister(conn)
            except KeyError:
                pass

            conn.close()

        # Cerramos el servidor.
        try:
            sel.unregister(servidor)
        except KeyError:
            pass

        servidor.close()

        sel.close()


# ------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------

if __name__ == '__main__':
    main()