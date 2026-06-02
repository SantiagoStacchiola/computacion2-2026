import threading
import time

class ContadorHilo(threading.Thread):
    def __init__(self, nombre, limite):
        super().__init__(name=nombre)
        self.limite = limite
        self.resultado = ""

    def run(self):
        numeros = []
        for i in range(1, self.limite + 1):
            numeros.append(str(i))
            time.sleep(0.1)
        self.resultado = ", ".join(numeros)

hilos = [
    ContadorHilo(f"Contador-{i}", limite)
    for i, limite in enumerate([5, 8, 3], 1)
]

for h in hilos: h.start()
for h in hilos: h.join()

for h in hilos:
    print(f"[{h.name}] resultado: {h.resultado}")