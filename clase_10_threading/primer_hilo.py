import threading
import random
import time

def imprimir_numeros(nombre):
        print(f"[{nombre}] número: {random.randint(1, 5)}")
        time.sleep(0.2)

hilos = [
    threading.Thread(target=imprimir_numeros, args=(f"Hilo-{i}",))
    for i in range(1, 4)
]

for h in hilos:
    h.start()

for h in hilos:
    h.join()

print("Listo")