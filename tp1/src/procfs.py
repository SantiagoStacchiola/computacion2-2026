# src/procfs.py

from pathlib import Path
import os


PROC = Path("/proc")
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


def rss_a_bytes(rss_paginas):
    return rss_paginas * PAGE_SIZE


def obtener_pids():
    """
    Devuelve una lista de PIDs existentes.
    """
    return sorted(
        int(p.name)
        for p in PROC.iterdir()
        if p.is_dir() and p.name.isdigit()
    )


def leer_meminfo():
    """
    Lee /proc/meminfo y devuelve un diccionario.
    """
    info = {}

    with open("/proc/meminfo", "r") as archivo:
        for linea in archivo:
            partes = linea.split()
            if len(partes) < 2:
                continue
            clave = partes[0].rstrip(":")
            valor = int(partes[1])
            info[clave] = valor

    return info


def leer_cpu_global():
    """
    Lee la línea CPU global de /proc/stat.
    """
    with open("/proc/stat", "r") as archivo:
        primera_linea = archivo.readline()

    campos = primera_linea.split()

    return {
        "user": int(campos[1]),
        "nice": int(campos[2]),
        "system": int(campos[3]),
        "idle": int(campos[4]),
        "iowait": int(campos[5]),
        "irq": int(campos[6]),
        "softirq": int(campos[7]),
    }


def leer_stat(pid):
    """
    Lee /proc/[pid]/stat de forma robusta.
    """
    ruta = f"/proc/{pid}/stat"

    with open(ruta, "r") as archivo:
        contenido = archivo.read().strip()

    inicio = contenido.find("(")
    fin = contenido.rfind(")")
    if inicio == -1 or fin == -1 or fin < inicio:
        raise ValueError(f"No se pudo parsear /proc/{pid}/stat")

    pid_texto = contenido[:inicio].strip()
    comm = contenido[inicio + 1:fin]
    resto = contenido[fin + 2:].split()

    campos = [pid_texto, comm] + resto

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
    """
    Lee /proc/[pid]/status.
    """
    ruta = f"/proc/{pid}/status"

    datos = {}

    with open(ruta, "r") as archivo:
        for linea in archivo:
            if ":" not in linea:
                continue

            clave, valor = linea.split(":", 1)
            datos[clave.strip()] = valor.strip()

    return datos


def leer_cmdline(pid):
    """
    Lee el comando completo utilizado para lanzar el proceso.
    """
    ruta = f"/proc/{pid}/cmdline"

    with open(ruta, "rb") as archivo:
        contenido = archivo.read()

    return contenido.replace(b"\0", b" ").decode(errors="ignore").strip()


def leer_loadavg():
    """
    Lee /proc/loadavg.
    """
    with open("/proc/loadavg", "r") as archivo:
        linea = archivo.readline()

    campos = linea.split()

    return {
        "load1": float(campos[0]),
        "load5": float(campos[1]),
        "load15": float(campos[2]),
        "procesos_corriendo": int(campos[3].split("/")[0]),
        "procesos_totales": int(campos[3].split("/")[1]),
        "ultimo_pid": int(campos[4]),
    }


def leer_uptime():
    """
    Lee /proc/uptime.
    """
    with open("/proc/uptime", "r") as archivo:
        linea = archivo.readline()

    campos = linea.split()

    return {
        "uptime": float(campos[0]),
        "idle_time": float(campos[1]),
    }


def leer_btime():
    """
    Lee el boot time de /proc/stat (btime en segundos desde epoch).
    """
    with open("/proc/stat", "r") as archivo:
        for linea in archivo:
            if linea.startswith("btime"):
                campos = linea.split()
                return int(campos[1])

    return 0


def leer_maps(pid):
    """
    Lee /proc/[pid]/maps y agrupa segmentos por permisos.
    """
    ruta = f"/proc/{pid}/maps"
    segmentos = []

    try:
        with open(ruta, "r") as archivo:
            for linea in archivo:
                partes = linea.split()
                if len(partes) < 6:
                    continue

                rango = partes[0]
                permisos = partes[1]
                offset = partes[2]
                dev = partes[3]
                inode = partes[4]
                path = " ".join(partes[5:]) if len(partes) > 5 else ""

                # Parsear rango
                inicio, fin = rango.split("-")
                tamano = int(fin, 16) - int(inicio, 16)

                segmentos.append({
                    "inicio": inicio,
                    "fin": fin,
                    "tamano": tamano,
                    "permisos": permisos,
                    "offset": offset,
                    "dev": dev,
                    "inode": inode,
                    "path": path,
                })
    except (FileNotFoundError, PermissionError):
        pass

    return segmentos


def extraer_memoria_de_status(status):
    """
    Extrae campos de memoria de /proc/[pid]/status.
    """
    memoria = {}

    campos_esperados = [
        "VmSize", "VmRSS", "VmData", "VmStk", "VmExe", "VmLib",
        "VmHWM", "VmSwap", "MinFlt", "MajFlt"
    ]

    for campo in campos_esperados:
        if campo in status:
            valor_texto = status[campo]
            # Formato: "123 kB" → extraer número
            numero = int(valor_texto.split()[0])
            memoria[campo] = numero
        else:
            memoria[campo] = 0

    return memoria


def leer_fds(pid):
    """
    Lee los file descriptors abiertos por un proceso.
    """
    ruta = f"/proc/{pid}/fd"
    fds = []

    try:
        for fd_name in sorted(os.listdir(ruta)):
            try:
                fd_path = os.path.join(ruta, fd_name)
                destino = os.readlink(fd_path)

                # Inferir tipo
                if destino.startswith("/"):
                    tipo = "file"
                elif destino.startswith("socket"):
                    tipo = "socket"
                elif destino.startswith("pipe"):
                    tipo = "pipe"
                elif "anon_inode" in destino:
                    if "eventfd" in destino:
                        tipo = "eventfd"
                    elif "timerfd" in destino:
                        tipo = "timerfd"
                    else:
                        tipo = "anon"
                else:
                    tipo = "other"

                fds.append({
                    "fd": int(fd_name),
                    "destino": destino,
                    "tipo": tipo,
                })
            except (OSError, ValueError):
                pass

    except (FileNotFoundError, PermissionError):
        pass

    return fds


def leer_threads(pid):
    """
    Lee los threads (LWPs) de un proceso.
    """
    ruta = f"/proc/{pid}/task"
    threads = []

    try:
        for tid_name in sorted(os.listdir(ruta)):
            try:
                tid = int(tid_name)
                stat_path = f"{ruta}/{tid}/stat"

                with open(stat_path, "r") as archivo:
                    contenido = archivo.read().strip()

                inicio = contenido.find("(")
                fin = contenido.rfind(")")
                if inicio == -1 or fin == -1 or fin < inicio:
                    continue

                resto = contenido[fin + 2:].split()

                estado = resto[0]
                utime = int(resto[11])
                stime = int(resto[12])

                comm_path = f"{ruta}/{tid}/comm"
                try:
                    with open(comm_path, "r") as archivo_comm:
                        comm = archivo_comm.read().strip()
                except:
                    comm = contenido[inicio + 1:fin]

                threads.append({
                    "tid": tid,
                    "comm": comm,
                    "estado": estado,
                    "utime": utime,
                    "stime": stime,
                })

            except (OSError, ValueError):
                pass

    except (FileNotFoundError, PermissionError):
        pass

    return threads


def extraer_cambios_de_contexto(status):
    """
    Extrae voluntary y nonvoluntary context switches desde /proc/[pid]/status.
    """
    return {
        "voluntary_ctxt_switches": int(
            status.get("voluntary_ctxt_switches", "0").split()[0]
        ),
        "nonvoluntary_ctxt_switches": int(
            status.get("nonvoluntary_ctxt_switches", "0").split()[0]
        ),
    }


def decodificar_señales(mascara_hex):
    """
    Decodifica una máscara hexadecimal de señales a una lista de nombres.
    """
    SENALES = {
        1: "SIGHUP",
        2: "SIGINT",
        3: "SIGQUIT",
        4: "SIGILL",
        5: "SIGTRAP",
        6: "SIGABRT",
        7: "SIGBUS",
        8: "SIGFPE",
        9: "SIGKILL",
        10: "SIGUSR1",
        11: "SIGSEGV",
        12: "SIGUSR2",
        13: "SIGPIPE",
        14: "SIGALRM",
        15: "SIGTERM",
        16: "SIGSTKFLT",
        17: "SIGCHLD",
        18: "SIGCONT",
        19: "SIGSTOP",
        20: "SIGTSTP",
        21: "SIGTTIN",
        22: "SIGTTOU",
        23: "SIGURG",
        24: "SIGXCPU",
        25: "SIGXFSZ",
        26: "SIGVTALRM",
        27: "SIGPROF",
        28: "SIGWINCH",
        29: "SIGIO",
        30: "SIGPWR",
        31: "SIGSYS",
    }

    try:
        valor = int(mascara_hex, 16)
    except (ValueError, TypeError):
        return []

    senales = []
    for num, nombre in SENALES.items():
        if valor & (1 << (num - 1)):
            senales.append(nombre)

    return senales