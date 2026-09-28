'''
import socket
import time


def conectar_con_reintentos(host, puerto, intentos=5):
    espera = 1

    for intento in range(1, intentos + 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((host, puerto))

            print(f"Conectado en el intento {intento}")
            return s

        except ConnectionRefusedError:
            s.close()

            print(f"Intento {intento}: servidor no disponible")

            if intento == intentos:
                print("Se agotaron los intentos")
                raise

            print(f"Esperando {espera} segundos...")
            time.sleep(espera)

            espera *= 2


s = conectar_con_reintentos("localhost", 8080)

print("Conexión establecida")

s.close()
'''
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("localhost", 8080))

s.settimeout(3)

print("Conectado")
print("Esperando datos...")

datos = s.recv(4096)

print(datos)