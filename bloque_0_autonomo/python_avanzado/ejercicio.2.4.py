from functools import wraps

def pipeline(*funciones):
    def aplicar_o_decorar(valor_o_funcion):
        # Caso 1: se usa como decorador
        if callable(valor_o_funcion) and hasattr(valor_o_funcion, "__name__"):
            func = valor_o_funcion

            @wraps(func)
            def wrapper(*args, **kwargs):
                resultado = func(*args, **kwargs)
                for funcion in funciones:
                    resultado = funcion(resultado)
                return resultado

            return wrapper

        # Caso 2: se usa como pipeline normal
        valor = valor_o_funcion
        for funcion in funciones:
            valor = funcion(valor)
        return valor

    return aplicar_o_decorar


def doble(x):
    return x * 2

def sumar_uno(x):
    return x + 1

def cuadrado(x):
    return x ** 2


# Uso normal
p = pipeline(doble, sumar_uno, cuadrado)

print(p(3))   # 49
print(p(5))   # 121

p2 = pipeline(doble)
print(p2(10))  # 20

p3 = pipeline(str, len, doble)
print(p3(12345))  # 10


# Uso como decorador
@pipeline(str.strip, str.lower, str.split)
def procesar_entrada(texto):
    return texto

print(procesar_entrada("  HELLO WORLD  "))  # ['hello', 'world']