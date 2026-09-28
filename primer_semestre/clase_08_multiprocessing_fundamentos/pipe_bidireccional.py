#!/usr/bin/env python3
"""Ping-pong con Pipe."""

from multiprocessing import Process, Pipe

def hijo(conn):
    for i in range(5):
        msg = conn.recv()
        print(f"[HIJO] Recibí: {msg}")

        respuesta = f"pong {i}"
        conn.send(respuesta)

    conn.close()


if __name__ == "__main__":
    padre_conn, hijo_conn = Pipe()

    p = Process(target=hijo, args=(hijo_conn,))
    p.start()

    for i in range(5):
        mensaje = f"ping {i}"

        print(f"[PADRE] Enviando: {mensaje}")
        padre_conn.send(mensaje)

        respuesta = padre_conn.recv()
        print(f"[PADRE] Recibí: {respuesta}")

    padre_conn.close()

    p.join()