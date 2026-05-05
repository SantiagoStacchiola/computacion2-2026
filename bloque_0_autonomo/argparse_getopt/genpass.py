import argparse
import secrets
import string

parser = argparse.ArgumentParser(
    description="Generador de contraseñas seguras"
)

parser.add_argument(
    "-n", "--length",
    type=int,
    default=12,
    help="Longitud de la contraseña"
)

parser.add_argument(
    "--no-symbols",
    action="store_true",
    help="Excluir símbolos"
)

parser.add_argument(
    "--no-numbers",
    action="store_true",
    help="Excluir números"
)

parser.add_argument(
    "--count",
    type=int,
    default=1,
    help="Cantidad de contraseñas"
)

args = parser.parse_args()

# pool de caracteres
caracteres = string.ascii_letters  # letras

if not args.no_numbers:
    caracteres += string.digits

if not args.no_symbols:
    caracteres += "!@#$%&"

# generar contraseñas
for _ in range(args.count):
    password = "".join(secrets.choice(caracteres) for _ in range(args.length))
    print(password)