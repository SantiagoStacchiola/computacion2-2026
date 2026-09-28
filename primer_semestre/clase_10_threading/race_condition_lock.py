import threading
import time

# Versión CON race condition
saldo_inseguro = 1000

def retirar_inseguro(monto):
    global saldo_inseguro
    if saldo_inseguro >= monto:
        time.sleep(0.001)
        saldo_inseguro -= monto

hilos = [threading.Thread(target=retirar_inseguro, args=(200,)) for _ in range(10)]
for h in hilos: h.start()
for h in hilos: h.join()
print(f"Saldo inseguro final: ${saldo_inseguro} (puede ser negativo)")

# Versión CORREGIDA con Lock
saldo_seguro = 1000
lock = threading.Lock()

def retirar_seguro(monto):
    global saldo_seguro
    with lock:
        if saldo_seguro >= monto:
            time.sleep(0.001)
            saldo_seguro -= monto
            print(f"Retiro de ${monto} OK. Saldo: ${saldo_seguro}")
        else:
            print(f"Saldo insuficiente para ${monto}. Saldo: ${saldo_seguro}")

hilos = [threading.Thread(target=retirar_seguro, args=(200,)) for _ in range(10)]
for h in hilos: h.start()
for h in hilos: h.join()
print(f"Saldo seguro final: ${saldo_seguro}")