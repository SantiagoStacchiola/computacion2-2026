# src/procfs.py

import os
import signal
from pathlib import Path


PROC = Path("/proc")
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


def rss_a_bytes(rss_paginas):
    return rss_paginas * PAGE_SIZE


def obtener_pids():
    """Devuelve los PIDs existentes en /proc."""
    try:
        return sorted(
            int(entrada.name)
            for entrada in PROC.iterdir()
            if entrada.is_dir() and entrada.name.isdigit()
        )
    except OSError:
        return []


def leer_meminfo():
    info = {}
    with open("/proc/meminfo", "r", encoding="utf-8") as archivo:
        for linea in archivo:
            partes = linea.split()
            if len(partes) >= 2:
                info[partes[0].rstrip(":")] = int(partes[1])
    return info


def leer_cpu_global():
    with open("/proc/stat", "r", encoding="utf-8") as archivo:
        campos = archivo.readline().split()

    valores = [int(valor) for valor in campos[1:]]
    valores += [0] * (8 - len(valores))

    return {
        "user": valores[0],
        "nice": valores[1],
        "system": valores[2],
        "idle": valores[3],
        "iowait": valores[4],
        "irq": valores[5],
        "softirq": valores[6],
        "steal": valores[7],
    }


def total_jiffies(cpu):
    return sum(int(valor) for valor in cpu.values())


def leer_stat(pid):
    """Lee /proc/<pid>/stat sin romperse si comm contiene espacios."""
    ruta = f"/proc/{pid}/stat"
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido = archivo.read().strip()

    inicio = contenido.find("(")
    fin = contenido.rfind(")")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ValueError(f"No se pudo parsear {ruta}")

    pid_texto = contenido[:inicio].strip()
    comm = contenido[inicio + 1:fin]
    resto = contenido[fin + 2:].split()
    campos = [pid_texto, comm] + resto

    if len(campos) <= 40:
        raise ValueError(f"{ruta} no contiene suficientes campos")

    return {
        "pid": int(campos[0]),
        "comm": campos[1],
        "state": campos[2],
        "ppid": int(campos[3]),
        "pgid": int(campos[4]),
        "sid": int(campos[5]),
        "minflt": int(campos[9]),
        "cminflt": int(campos[10]),
        "majflt": int(campos[11]),
        "cmajflt": int(campos[12]),
        "utime": int(campos[13]),
        "stime": int(campos[14]),
        "priority": int(campos[17]),
        "nice": int(campos[18]),
        "num_threads": int(campos[19]),
        "vsize": int(campos[22]),
        "rss": int(campos[23]),
        "rt_priority": int(campos[39]),
        "policy": int(campos[40]),
    }


def leer_status(pid):
    datos = {}
    with open(f"/proc/{pid}/status", "r", encoding="utf-8") as archivo:
        for linea in archivo:
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                datos[clave.strip()] = valor.strip()
    return datos


def leer_cmdline(pid):
    with open(f"/proc/{pid}/cmdline", "rb") as archivo:
        contenido = archivo.read()
    return contenido.replace(b"\0", b" ").decode(errors="ignore").strip()


def leer_loadavg():
    with open("/proc/loadavg", "r", encoding="utf-8") as archivo:
        campos = archivo.readline().split()

    corriendo, totales = campos[3].split("/", 1)
    return {
        "load1": float(campos[0]),
        "load5": float(campos[1]),
        "load15": float(campos[2]),
        "procesos_corriendo": int(corriendo),
        "procesos_totales": int(totales),
        "ultimo_pid": int(campos[4]),
    }


def leer_uptime():
    with open("/proc/uptime", "r", encoding="utf-8") as archivo:
        campos = archivo.readline().split()
    return {"uptime": float(campos[0]), "idle_time": float(campos[1])}


def leer_btime():
    with open("/proc/stat", "r", encoding="utf-8") as archivo:
        for linea in archivo:
            if linea.startswith("btime "):
                return int(linea.split()[1])
    return 0


def leer_maps(pid):
    """Lee todos los segmentos, incluidos los mapeos anónimos sin pathname."""
    segmentos = []
    try:
        with open(f"/proc/{pid}/maps", "r", encoding="utf-8") as archivo:
            for linea in archivo:
                partes = linea.rstrip("\n").split(maxsplit=5)
                if len(partes) < 5:
                    continue

                rango, permisos, offset, dev, inode = partes[:5]
                path = partes[5] if len(partes) == 6 else ""
                inicio, fin = rango.split("-", 1)

                segmentos.append({
                    "inicio": inicio,
                    "fin": fin,
                    "tamano": int(fin, 16) - int(inicio, 16),
                    "permisos": permisos,
                    "offset": offset,
                    "dev": dev,
                    "inode": inode,
                    "path": path,
                })
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass

    return segmentos


def extraer_memoria_de_status(status):
    campos = (
        "VmSize", "VmRSS", "VmData", "VmStk", "VmExe", "VmLib",
        "VmHWM", "VmSwap",
    )
    memoria = {}
    for campo in campos:
        try:
            memoria[campo] = int(status.get(campo, "0").split()[0])
        except (ValueError, IndexError):
            memoria[campo] = 0
    return memoria


def leer_fds(pid):
    ruta = f"/proc/{pid}/fd"
    fds = []

    try:
        nombres = sorted(os.listdir(ruta), key=lambda valor: int(valor))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return fds

    for fd_name in nombres:
        try:
            destino = os.readlink(os.path.join(ruta, fd_name))

            if destino.startswith("/dev/tty") or destino.startswith("/dev/pts/"):
                tipo = "tty"
            elif destino.startswith("socket:"):
                tipo = "socket"
            elif destino.startswith("pipe:"):
                tipo = "pipe"
            elif destino.startswith("anon_inode:"):
                if "eventfd" in destino:
                    tipo = "eventfd"
                elif "timerfd" in destino:
                    tipo = "timerfd"
                elif "eventpoll" in destino:
                    tipo = "epoll"
                else:
                    tipo = "anon"
            elif destino.startswith("/"):
                tipo = "file"
            else:
                tipo = "other"

            fds.append({
                "fd": int(fd_name),
                "destino": destino,
                "tipo": tipo,
            })
        except (OSError, ValueError):
            continue

    return fds


def leer_threads(pid):
    ruta = f"/proc/{pid}/task"
    threads = []

    try:
        tids = sorted(os.listdir(ruta), key=lambda valor: int(valor))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return threads

    for tid_name in tids:
        try:
            tid = int(tid_name)
            base = f"{ruta}/{tid}"

            with open(f"{base}/stat", "r", encoding="utf-8") as archivo:
                contenido = archivo.read().strip()

            inicio = contenido.find("(")
            fin = contenido.rfind(")")
            if inicio == -1 or fin == -1 or fin < inicio:
                continue

            resto = contenido[fin + 2:].split()
            estado = resto[0]
            utime = int(resto[11])
            stime = int(resto[12])

            try:
                with open(f"{base}/comm", "r", encoding="utf-8") as archivo:
                    comm = archivo.read().strip()
            except OSError:
                comm = contenido[inicio + 1:fin]

            status = {}
            with open(f"{base}/status", "r", encoding="utf-8") as archivo:
                for linea in archivo:
                    if ":" in linea:
                        clave, valor = linea.split(":", 1)
                        status[clave.strip()] = valor.strip()

            cambios = extraer_cambios_de_contexto(status)
            threads.append({
                "tid": tid,
                "comm": comm,
                "estado": estado,
                "utime": utime,
                "stime": stime,
                **cambios,
            })
        except (OSError, ValueError, IndexError):
            continue

    return threads


def extraer_cambios_de_contexto(status):
    def entero(clave):
        try:
            return int(status.get(clave, "0").split()[0])
        except (ValueError, IndexError):
            return 0

    return {
        "voluntary_ctxt_switches": entero("voluntary_ctxt_switches"),
        "nonvoluntary_ctxt_switches": entero("nonvoluntary_ctxt_switches"),
    }


def nombre_senal(numero):
    try:
        return signal.Signals(numero).name
    except ValueError:
        sig_rt_min = int(signal.SIGRTMIN)
        sig_rt_max = int(signal.SIGRTMAX)
        if sig_rt_min <= numero <= sig_rt_max:
            desplazamiento = numero - sig_rt_min
            return "SIGRTMIN" if desplazamiento == 0 else f"SIGRTMIN+{desplazamiento}"
        return f"SIG{numero}"


def decodificar_señales(mascara_hex):
    """Decodifica los 64 bits de SigBlk/SigIgn/SigCgt/SigPnd/ShdPnd."""
    try:
        valor = int(mascara_hex, 16)
    except (TypeError, ValueError):
        return []

    return [
        nombre_senal(numero)
        for numero in range(1, 65)
        if valor & (1 << (numero - 1))
    ]