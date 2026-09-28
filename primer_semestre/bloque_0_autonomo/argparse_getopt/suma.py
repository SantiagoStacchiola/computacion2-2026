import sys

suma = 0

for arg in sys.argv[1:]:
    try:
        numero = float(arg)  # permite enteros y decimales
        suma += numero
    except ValueError:
        print(f"Advertencia: '{arg}' no es un número válido y será ignorado")

print(f"Suma: {suma}")