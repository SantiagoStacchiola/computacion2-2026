#!/usr/bin/env python3
"""Filósofos comensales: del deadlock a la solución."""
import threading
import time
import random

NUM = 5


# ---- Parte A: la versión que se cuelga ----
# Cada filósofo toma primero su tenedor izquierdo, después el derecho.
#
# El deadlock necesita que los cinco tengan su tenedor izquierdo al mismo
# tiempo. Con sleeps al azar eso pasa rara vez (probalo: puede que corra
# entero muchas veces seguidas). Para hacerlo determinista forzamos ese
# estado con una Barrier: nadie pide el derecho hasta que todos tengan
# el izquierdo. Es hacer trampa, pero muestra el escenario exacto que en
# producción aparece una vez cada mil corridas.

def comer(id):
    time.sleep(random.uniform(0.01, 0.05))
    print(f"Filósofo {id} come")


def filosofo_ingenuo(id, tenedores, barrier):
    for _ in range(3):
        izq, der = id, (id + 1) % NUM
        with tenedores[izq]:
            barrier.wait()  # los 5 ya tienen su izquierdo
            with tenedores[der]:  # ...y ninguno va a conseguir el derecho
                comer(id)


# En este caso se cumplen las cuatro condiciones de Coffman:
# 1) exclusión mutua: un tenedor solo puede ser usado por un filósofo;
# 2) retención y espera: cada filósofo retiene su izquierdo y espera el derecho;
# 3) no apropiación preventiva: nadie puede quitarle el tenedor a otro;
# 4) espera circular: cada filósofo espera al siguiente, formando un ciclo.
#
# La barrera hace el deadlock determinista; sin ella el problema sigue existiendo,
# pero aparece con baja probabilidad, por eso es difícil de reproducir en pruebas.


def demo_deadlock():
    print("\n=== Parte A: deadlock determinista ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    barrier = threading.Barrier(NUM)
    hilos = [
        threading.Thread(target=filosofo_ingenuo, args=(i, tenedores, barrier), daemon=True)
        for i in range(NUM)
    ]

    for hilo in hilos:
        hilo.start()

    time.sleep(1.0)
    vivos = [hilo.is_alive() for hilo in hilos]
    for hilo in hilos:
        hilo.join(timeout=0.1)

    print(f"Hilos vivos después de 1 segundo: {vivos}")
    if all(vivos):
        print("Resultado: deadlock detectado (todos quedaron esperando).")
    else:
        print("No se detectó deadlock en esta ejecución, pero el patrón es real.")


# ---- Parte B: jerarquía de recursos ----
# Reimplementamos la toma de tenedores ordenando índices: cada filósofo toma
# primero el tenedor de MENOR índice y luego el de MAYOR índice. Esto evita la
# espera circular porque todos respetan la misma regla de ordenación.

def filosofo_jerarquia(id, tenedores):
    for _ in range(3):
        izq, der = id, (id + 1) % NUM
        primero, segundo = sorted((izq, der))
        with tenedores[primero]:
            with tenedores[segundo]:
                comer(id)


def demo_jerarquia():
    print("\n=== Parte B: jerarquía de recursos ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    hilos = [
        threading.Thread(target=filosofo_jerarquia, args=(i, tenedores))
        for i in range(NUM)
    ]

    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    print("Resultado: la versión ordenada termina sin deadlock.")


# ---- Parte C: limitar comensales ----
# Vuelta a la versión ingenua, pero con un semáforo que permite a lo sumo N-1
# filósofos dentro de la zona de comida. Eso elimina la posibilidad de que se
# formen todos los que toman el izquierdo y esperan el derecho.
# ¿Por qué basta con N-1? Porque si como mucho N-1 están comiendo, al menos
# un filósofo queda afuera y la espera circular no puede cerrarse completamente.

def filosofo_limitado(id, tenedores, puede_comer):
    for _ in range(3):
        izq, der = id, (id + 1) % NUM
        with puede_comer:
            with tenedores[izq]:
                with tenedores[der]:
                    comer(id)


def demo_limitador():
    print("\n=== Parte C: limitar comensales ===")
    tenedores = [threading.Lock() for _ in range(NUM)]
    puede_comer = threading.Semaphore(NUM - 1)
    hilos = [
        threading.Thread(target=filosofo_limitado, args=(i, tenedores, puede_comer))
        for i in range(NUM)
    ]

    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    print("Resultado: con N-1 comensales simultáneos tampoco se cuelga.")


# ---- Parte D: comparación ----
# Para medir, tomamos el tiempo de inicio de cada filósofo y el tiempo al
# terminar sus 3 comidas. Así vemos si alguna solución deja a alguien mucho más
# lento que el resto. La comparación se hace sobre los tiempos por filósofo y
# el tiempo total del grupo.

def medir_solucion(nombre, filosofia, start_barrier=None, recurso_extra=None):
    tenedores = [threading.Lock() for _ in range(NUM)]
    tiempos = [None] * NUM
    inicio_total = time.perf_counter()

    def worker(id):
        if start_barrier is not None:
            start_barrier.wait()
        if recurso_extra is not None:
            filosofia(id, tenedores, recurso_extra)
        else:
            filosofia(id, tenedores)
        tiempos[id] = time.perf_counter() - inicio_total

    hilos = [threading.Thread(target=worker, args=(i,)) for i in range(NUM)]

    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    print(f"{nombre}: tiempos por filósofo = {tiempos}")
    print(f"  total del grupo: {time.perf_counter() - inicio_total:.3f} s")
    print(f"  rango: {min(t for t in tiempos if t is not None):.3f}s a {max(t for t in tiempos if t is not None):.3f}s")


def demo_comparacion():
    print("\n=== Parte D: comparación ===")
    inicio = threading.Barrier(NUM)
    medir_solucion("Jerarquía de recursos", filosofo_jerarquia, inicio)

    inicio2 = threading.Barrier(NUM)
    semaforo_compartido = threading.Semaphore(NUM - 1)
    medir_solucion("Semáforo N-1", filosofo_limitado, inicio2, semaforo_compartido)


def main():
    demo_deadlock()
    demo_jerarquia()
    demo_limitador()
    demo_comparacion()


if __name__ == "__main__":
    main()