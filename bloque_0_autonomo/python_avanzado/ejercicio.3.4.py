from functools import wraps
from inspect import signature


def validate_types(func):
    sig = signature(func)
    annotations = func.__annotations__

    @wraps(func)
    def wrapper(*args, **kwargs):
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Validar argumentos
        for nombre, valor in bound_args.arguments.items():
            if nombre in annotations:
                tipo_esperado = annotations[nombre]

                if not isinstance(valor, tipo_esperado):
                    raise TypeError(
                        f"'{nombre}' debe ser {tipo_esperado.__name__}, recibido {type(valor).__name__}"
                    )

        resultado = func(*args, **kwargs)

        # Validar retorno
        if "return" in annotations:
            tipo_retorno = annotations["return"]

            if not isinstance(resultado, tipo_retorno):
                raise TypeError(
                    f"retorno debe ser {tipo_retorno.__name__}, recibido {type(resultado).__name__}"
                )

        return resultado

    return wrapper


@validate_types
def procesar(nombre: str, edad: int, activo: bool = True) -> str:
    return f"{nombre} tiene {edad} años"


print(procesar("Ana", 25))
print(procesar("Ana", 25, False))

# Descomentá para probar errores:
# print(procesar("Ana", "25"))
# print(procesar(123, 25))


@validate_types
def sumar(a: int, b: int) -> int:
    return str(a + b)   # Error a propósito


# Descomentá para probar error de retorno:
# print(sumar(1, 2))