import threading
import time

URLS = [f"http://servidor.com/archivo_{i}.zip" for i in range(5)]
DEMORA = 1  # segundos por descarga

def simular_descarga(url, demora):
    time.sleep(demora)
    print(f"Descargado: {url}")

# Secuencial
inicio = time.perf_counter()
for url in URLS:
    simular_descarga(url, DEMORA)
tiempo_secuencial = time.perf_counter() - inicio
print(f"\nSecuencial: {tiempo_secuencial:.2f}s")

# Paralelo con threading
inicio = time.perf_counter()
hilos = [
    threading.Thread(target=simular_descarga, args=(url, DEMORA))
    for url in URLS
]
for h in hilos: h.start()
for h in hilos: h.join()
tiempo_paralelo = time.perf_counter() - inicio
print(f"Threading:  {tiempo_paralelo:.2f}s")
print(f"Mejora:     {tiempo_secuencial / tiempo_paralelo:.1f}x")