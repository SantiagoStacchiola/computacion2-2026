import time
from contextlib import contextmanager


# =========================
# 1) Implementación con clase
# =========================
class Timer:
    def __init__(self, nombre=None):
        self.nombre = nombre
        self.inicio = None
        self.fin = None

    def __enter__(self):
        self.inicio = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fin = time.perf_counter()

        if self.nombre:
            print(f"[Timer] {self.nombre}: {self.elapsed:.3f}s")

    @property
    def elapsed(self):
        if self.inicio is None:
            return 0
        if self.fin is None:
            return time.perf_counter() - self.inicio
        return self.fin - self.inicio


# =========================
# 2) Implementación con @contextmanager
# =========================
class MedicionTiempo:
    def __init__(self, nombre=None):
        self.nombre = nombre
        self.inicio = None
        self.fin = None

    @property
    def elapsed(self):
        if self.inicio is None:
            return 0
        if self.fin is None:
            return time.perf_counter() - self.inicio
        return self.fin - self.inicio


@contextmanager
def timer(nombre=None):
    t = MedicionTiempo(nombre)
    t.inicio = time.perf_counter()
    try:
        yield t
    finally:
        t.fin = time.perf_counter()
        if t.nombre:
            print(f"[Timer] {t.nombre}: {t.elapsed:.3f}s")


# =========================
# PRUEBAS
# =========================
print("=== Usando la clase Timer ===")
with Timer("Procesamiento de datos"):
    datos = [x**2 for x in range(1000000)]

with Timer() as t:
    time.sleep(0.5)
print(f"El bloque tardó {t.elapsed:.3f} segundos")

with Timer() as t:
    time.sleep(0.3)
    print(f"Después del paso 1: {t.elapsed:.3f}s")
    time.sleep(0.2)
    print(f"Después del paso 2: {t.elapsed:.3f}s")


print("\n=== Usando timer con @contextmanager ===")
with timer("Procesamiento de datos"):
    datos = [x**2 for x in range(1000000)]

with timer() as t:
    time.sleep(0.5)
print(f"El bloque tardó {t.elapsed:.3f} segundos")

with timer() as t:
    time.sleep(0.3)
    print(f"Después del paso 1: {t.elapsed:.3f}s")
    time.sleep(0.2)
    print(f"Después del paso 2: {t.elapsed:.3f}s")