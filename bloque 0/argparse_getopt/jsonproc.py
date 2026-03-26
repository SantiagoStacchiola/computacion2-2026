import argparse
import json
import sys

parser = argparse.ArgumentParser(description="Procesador JSON")

parser.add_argument("archivo", help="Archivo JSON o '-' para stdin")

parser.add_argument("--keys", action="store_true")
parser.add_argument("--get")
parser.add_argument("--pretty", action="store_true")
parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"))
parser.add_argument("-o", "--output")

args = parser.parse_args()

# leer JSON
if args.archivo == "-":
    data = json.load(sys.stdin)
else:
    with open(args.archivo, encoding="utf-8") as f:
        data = json.load(f)

# helper para paths tipo usuario.nombre o productos.0.precio
def acceder(data, path):
    partes = path.split(".")
    actual = data

    for p in partes:
        if p.isdigit():
            actual = actual[int(p)]
        else:
            actual = actual[p]

    return actual

def asignar(data, path, valor):
    partes = path.split(".")
    actual = data

    for p in partes[:-1]:
        actual = actual[int(p)] if p.isdigit() else actual[p]

    ultimo = partes[-1]
    if ultimo.isdigit():
        actual[int(ultimo)] = json.loads(valor)
    else:
        actual[ultimo] = json.loads(valor)

# operaciones
if args.keys:
    for k in data.keys():
        print(k)

elif args.get:
    print(json.dumps(acceder(data, args.get), indent=4 if args.pretty else None))

elif args.set:
    key, value = args.set
    asignar(data, key, value)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Guardado en {args.output}")
    else:
        print(json.dumps(data, indent=4))

elif args.pretty:
    print(json.dumps(data, indent=4))