import argparse
import json
from pathlib import Path

archivo = Path.home() / ".tareas.json"

def cargar():
    if archivo.exists():
        return json.loads(archivo.read_text())
    return []

def guardar(tareas):
    archivo.write_text(json.dumps(tareas, indent=4))

parser = argparse.ArgumentParser(description="Gestor de tareas")
subparsers = parser.add_subparsers(dest="comando")

# add
p_add = subparsers.add_parser("add")
p_add.add_argument("descripcion")
p_add.add_argument("--priority", choices=["baja", "media", "alta"])

# list
p_list = subparsers.add_parser("list")
p_list.add_argument("--pending", action="store_true")
p_list.add_argument("--done", action="store_true")
p_list.add_argument("--priority", choices=["baja", "media", "alta"])

# done
p_done = subparsers.add_parser("done")
p_done.add_argument("id", type=int)

# remove
p_remove = subparsers.add_parser("remove")
p_remove.add_argument("id", type=int)

args = parser.parse_args()
tareas = cargar()

# lógica
if args.comando == "add":
    nueva = {
        "id": len(tareas) + 1,
        "desc": args.descripcion,
        "done": False,
        "priority": args.priority
    }
    tareas.append(nueva)
    guardar(tareas)
    print(f"Tarea #{nueva['id']} agregada")

elif args.comando == "list":
    for t in tareas:
        if args.pending and t["done"]:
            continue
        if args.done and not t["done"]:
            continue
        if args.priority and t["priority"] != args.priority:
            continue

        estado = "x" if t["done"] else " "
        prio = f" [{t['priority'].upper()}]" if t["priority"] else ""
        print(f"#{t['id']} [{estado}] {t['desc']}{prio}")

elif args.comando == "done":
    for t in tareas:
        if t["id"] == args.id:
            t["done"] = True
            guardar(tareas)
            print(f"Tarea #{args.id} completada")

elif args.comando == "remove":
    for t in tareas:
        if t["id"] == args.id:
            confirm = input(f"¿Eliminar \"{t['desc']}\"? [s/N] ")
            if confirm.lower() == "s":
                tareas.remove(t)
                guardar(tareas)
                print(f"Tarea #{args.id} eliminada")