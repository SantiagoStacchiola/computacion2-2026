import threading
import time
import math

def cpu_task(n):
    return sum(math.sqrt(i) for i in range(n))

N = 5_000_000

# Secuencial
inicio = time.perf_counter()
cpu_task(N)
print(f"Secuencial:  {time.perf_counter() - inicio:.2f}s")

# Con 4 threads
inicio = time.perf_counter()
hilos = [threading.Thread(target=cpu_task, args=(N,)) for _ in range(4)]
for h in hilos: h.start()
for h in hilos: h.join()
print(f"4 threads:   {time.perf_counter() - inicio:.2f}s")