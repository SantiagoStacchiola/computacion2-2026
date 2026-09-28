from contextlib import contextmanager
import os

@contextmanager
def archivo_temporal(nombre_archivo):
    archivo = open(nombre_archivo, "w+")
    try:
        yield archivo
    finally:
        archivo.close()
        if os.path.exists(nombre_archivo):
            os.remove(nombre_archivo)


with archivo_temporal("test.txt") as f:
    f.write("Datos de prueba\n")
    f.write("Más datos\n")
    f.seek(0)
    print(f.read())

assert not os.path.exists("test.txt")
print("El archivo fue borrado correctamente")