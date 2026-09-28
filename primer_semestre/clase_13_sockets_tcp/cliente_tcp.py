import socket

HOST = "localhost"
PORT = 8080

datos = b"x" * (10 * 1024 * 1024)  # 10 MB

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    enviados = s.send(datos)

    print(f"Bytes que intentamos enviar: {len(datos)}")
    print(f"Bytes enviados por send(): {enviados}")