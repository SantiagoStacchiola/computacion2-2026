"""
#!/usr/bin/env python3
#Mini-shell: paso 1 - loop básico.
import os

def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        if not linea.strip():
            continue

        if linea.strip() == "exit":
            break

        print(f"Comando recibido: {linea}")

if __name__ == "__main__":
    main()
"""

"""
#!/usr/bin/env python3
#Mini-shell: paso 2 - fork+exec.
import os

def main():
    while True:
        try:
            linea = input("minish$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue

        if linea == "exit":
            break

        # Parsear comando y argumentos
        partes = linea.split()
        comando = partes[0]
        args = partes[1:]

        # Fork + exec
        pid = os.fork()

        if pid == 0:
            try:
                os.execvp(comando, [comando] + args)
            except OSError as e:
                print(f"minish: {comando}: {e}")
                os._exit(127)
        else:
            _, status = os.wait()
            # Opcional: mostrar código si no es 0
            codigo = os.WEXITSTATUS(status)
            if codigo != 0:
                print(f"[código {codigo}]")

if __name__ == "__main__":
    main()
"""

#!/usr/bin/env python3
"""Mini-shell: paso 3 - comandos internos."""
import os

def cmd_cd(args):
    """Implementación del comando cd."""
    if not args:
        destino = os.environ.get("HOME", "/")
    else:
        destino = args[0]

    try:
        os.chdir(destino)
    except OSError as e:
        print(f"cd: {e}")

def main():
    # Comandos internos
    internos = {
        "cd": cmd_cd,
    }

    while True:
        # Mostrar directorio actual en el prompt
        cwd = os.getcwd()
        try:
            linea = input(f"minish:{cwd}$ ")
        except EOFError:
            print("\nChau!")
            break

        linea = linea.strip()
        if not linea:
            continue

        if linea == "exit":
            break

        partes = linea.split()
        comando = partes[0]
        args = partes[1:]

        # ¿Es comando interno?
        if comando in internos:
            internos[comando](args)
            continue

        # Comando externo: fork + exec
        pid = os.fork()

        if pid == 0:
            try:
                os.execvp(comando, [comando] + args)
            except OSError as e:
                print(f"minish: {comando}: {e}")
                os._exit(127)
        else:
            _, status = os.wait()
            codigo = os.WEXITSTATUS(status)
            if codigo != 0:
                print(f"[código {codigo}]")

if __name__ == "__main__":
    main()