from datetime import datetime
from functools import wraps

def log_llamada(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        argumentos = [repr(arg) for arg in args]
        argumentos += [f"{clave}={repr(valor)}" for clave, valor in kwargs.items()]
        argumentos_str = ", ".join(argumentos)

        print(f"[{timestamp}] Llamando a {func.__name__}({argumentos_str})")

        resultado = func(*args, **kwargs)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {func.__name__} retornó {repr(resultado)}")

        return resultado

    return wrapper


@log_llamada
def sumar(a, b):
    return a + b


@log_llamada
def saludar(nombre, entusiasta=False):
    sufijo = "!" if entusiasta else "."
    return f"Hola, {nombre}{sufijo}"


resultado = sumar(3, 5)
saludo = saludar("Ana", entusiasta=True)