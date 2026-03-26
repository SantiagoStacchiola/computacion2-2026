import sys

# 1. Validar argumento
if len(sys.argv) < 2:
    print("Error: Debe especificar un archivo")
    sys.exit()

archivo = sys.argv[1]

try:
    # 2. Intentar abrir el archivo
    with open(archivo, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    # 3. Contar líneas
    cantidad = len(lineas)
    print(f"{cantidad} líneas")

except FileNotFoundError:
    print(f"Error: No se puede leer '{archivo}'")

except PermissionError:
    print(f"Error: No tiene permisos para leer '{archivo}'")

except Exception:
    # Catch genérico (por si pasa algo raro)
    print(f"Error: No se puede leer '{archivo}'")