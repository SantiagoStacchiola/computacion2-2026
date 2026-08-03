# src/display.py

import curses
import time


class DisplayTUI:
    """Interfaz curses: lista de procesos arriba y detalle abajo."""

    VISTAS = {
        "1": "resumen",
        "2": "memoria",
        "3": "fds",
        "4": "threads",
        "5": "senales",
        "6": "scheduling",
        "7": "sistema",
        "r": "resumen",
        "m": "memoria",
        "f": "fds",
        "t": "threads",
        "s": "senales",
        "p": "scheduling",
        "g": "sistema",
    }

    INTERVALOS_MINIMOS = {
        "resumen": 0.5,
        "memoria": 1.0,
        "fds": 2.0,
        "threads": 0.5,
        "senales": 5.0,
        "scheduling": 5.0,
        "sistema": 1.0,
    }

    def __init__(self, snapshot, intervalos):
        self.snapshot = snapshot
        self.intervalos = intervalos

        estado = snapshot["estado_global"]
        self.vista_actual = estado.get("vista_activa", "resumen")
        self.filtro_comando = estado.get("filtro_comando", "")
        self.filtro_usuario = estado.get("filtro_usuario", "")
        self.ordenar_por = estado.get("ordenar_por", "cpu_percent")
        self.pid_pinned = estado.get("pid_pinned")
        self.config_version = int(estado.get("config_version", 0))

        self.indice_seleccionado = 0
        self.running = True
        self.mostrar_ayuda = False
        self.modo_entrada = None
        self.entrada_buffer = ""

        self.cache_resumen = []
        self.cache_vista = []
        self.version_resumen = -1
        self.version_vista = -1
        self.forzar_render = True

    @staticmethod
    def addstr_seguro(stdscr, fila, columna, texto, atributo=0):
        altura, ancho = stdscr.getmaxyx()
        if fila < 0 or fila >= altura or columna >= ancho:
            return
        disponible = max(0, ancho - columna - 1)
        try:
            stdscr.addstr(fila, columna, str(texto)[:disponible], atributo)
        except curses.error:
            pass

    def leer_intervalo(self):
        valor = self.intervalos[self.vista_actual]
        with valor.get_lock():
            return float(valor.value)

    def modificar_intervalo(self, delta):
        valor = self.intervalos[self.vista_actual]
        minimo = self.INTERVALOS_MINIMOS[self.vista_actual]
        with valor.get_lock():
            valor.value = min(30.0, max(minimo, valor.value + delta))
        self.forzar_render = True

    def sincronizar_configuracion(self, estado):
        version = int(estado.get("config_version", 0))
        if version == self.config_version:
            return

        self.vista_actual = estado.get("vista_activa", "resumen")
        self.filtro_comando = estado.get("filtro_comando", "")
        self.filtro_usuario = estado.get("filtro_usuario", "")
        self.ordenar_por = estado.get("ordenar_por", "cpu_percent")
        self.config_version = version
        self.indice_seleccionado = 0
        self.version_vista = -1
        self.forzar_render = True

    def actualizar_cache(self):
        slot_resumen = self.snapshot["resumen"]
        version_resumen = int(slot_resumen.get("version", 0))
        if version_resumen != self.version_resumen:
            self.cache_resumen = list(slot_resumen.get("data", []))
            self.version_resumen = version_resumen
            self.forzar_render = True

        slot_vista = self.snapshot[self.vista_actual]
        version_vista = int(slot_vista.get("version", 0))
        if version_vista != self.version_vista:
            datos = slot_vista.get("data", [])
            self.cache_vista = dict(datos) if isinstance(datos, dict) else list(datos)
            self.version_vista = version_vista
            self.forzar_render = True

    def obtener_procesos(self):
        procesos = list(self.cache_resumen)

        if self.filtro_comando:
            filtro = self.filtro_comando.lower()
            procesos = [
                proceso for proceso in procesos
                if filtro in proceso.get("nombre", "").lower()
                or filtro in proceso.get("cmdline", "").lower()
            ]

        if self.filtro_usuario:
            filtro = self.filtro_usuario.lower()
            procesos = [
                proceso for proceso in procesos
                if filtro in proceso.get("usuario", "").lower()
            ]

        if self.ordenar_por == "cpu_percent":
            procesos.sort(key=lambda proceso: proceso.get("cpu_percent", 0), reverse=True)
        elif self.ordenar_por == "rss_bytes":
            procesos.sort(key=lambda proceso: proceso.get("rss_bytes", 0), reverse=True)
        else:
            procesos.sort(key=lambda proceso: proceso.get("pid", 0))

        if self.pid_pinned is not None:
            for indice, proceso in enumerate(procesos):
                if proceso.get("pid") == self.pid_pinned:
                    self.indice_seleccionado = indice
                    break

        if procesos:
            self.indice_seleccionado = max(
                0,
                min(self.indice_seleccionado, len(procesos) - 1),
            )
        else:
            self.indice_seleccionado = 0

        return procesos

    def pid_activo(self, procesos):
        if self.pid_pinned is not None:
            return self.pid_pinned
        if not procesos:
            return None
        return procesos[self.indice_seleccionado]["pid"]

    @staticmethod
    def buscar_por_pid(datos, pid):
        if pid is None or isinstance(datos, dict):
            return None
        for elemento in datos:
            if elemento.get("pid") == pid:
                return elemento
        return None

    def render_lista(self, stdscr, procesos, filas_disponibles):
        self.addstr_seguro(
            stdscr,
            0,
            0,
            "=== MONITOR DE PROCESOS Y THREADS ===",
            curses.A_BOLD,
        )
        self.addstr_seguro(
            stdscr,
            1,
            0,
            f"Vista activa: {self.vista_actual.upper()} | "
            f"intervalo: {self.leer_intervalo():.1f}s",
        )
        self.addstr_seguro(
            stdscr,
            2,
            0,
            f"{'PID':>6} {'S':1} {'USUARIO':12} {'CPU%':>7} "
            f"{'RSS(MB)':>9} {'THR':>5} COMANDO",
            curses.A_BOLD,
        )

        if not procesos:
            self.addstr_seguro(stdscr, 3, 0, "Cargando procesos o sin coincidencias...")
            return

        inicio = max(0, self.indice_seleccionado - filas_disponibles + 1)
        fin = min(len(procesos), inicio + filas_disponibles)

        for fila, indice in enumerate(range(inicio, fin), start=3):
            proceso = procesos[indice]
            rss_mb = proceso.get("rss_bytes", 0) / (1024 * 1024)
            linea = (
                f"{proceso.get('pid', 0):6d} "
                f"{proceso.get('estado', '?')[:1]:1} "
                f"{proceso.get('usuario', '-')[:12]:12} "
                f"{proceso.get('cpu_percent', 0):7.2f} "
                f"{rss_mb:9.2f} "
                f"{proceso.get('threads', 0):5d} "
                f"{proceso.get('nombre', '')}"
            )
            atributo = curses.A_REVERSE if indice == self.indice_seleccionado else 0
            self.addstr_seguro(stdscr, fila, 0, linea, atributo)

    def render_detalle_resumen(self, stdscr, fila, proceso):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "Sin datos para el proceso seleccionado")
            return

        lineas = [
            f"PID={proceso['pid']} PPID={proceso.get('ppid')} "
            f"UID={proceso.get('uid')} GID={proceso.get('gid')} "
            f"estado={proceso.get('estado')}",
            f"CPU={proceso.get('cpu_percent', 0):.2f}% "
            f"RSS={proceso.get('rss_bytes', 0) / (1024 * 1024):.2f} MB "
            f"threads={proceso.get('threads', 0)}",
            f"Comando: {proceso.get('cmdline', proceso.get('nombre', ''))}",
        ]
        for desplazamiento, texto in enumerate(lineas):
            self.addstr_seguro(stdscr, fila + desplazamiento, 0, texto)

    def render_detalle_memoria(self, stdscr, fila, proceso):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "Memoria todavía no disponible")
            return

        memoria = proceso.get("memoria_campos", {})
        faults = proceso.get("faults", {})
        self.addstr_seguro(
            stdscr, fila, 0,
            " ".join(f"{campo}={memoria.get(campo, 0)}KB" for campo in (
                "VmSize", "VmRSS", "VmHWM", "VmData", "VmStk", "VmExe", "VmLib", "VmSwap"
            )),
        )
        self.addstr_seguro(
            stdscr, fila + 1, 0,
            f"Faults: minor={faults.get('minor_faults', 0)} "
            f"children_minor={faults.get('children_minor_faults', 0)} "
            f"major={faults.get('major_faults', 0)} "
            f"children_major={faults.get('children_major_faults', 0)}",
        )
        segmentos = proceso.get("segmentos_agrupados", {})
        texto = ", ".join(
            f"{tipo}={datos.get('tamano', 0) / (1024 * 1024):.1f}MB"
            for tipo, datos in segmentos.items()
        )
        self.addstr_seguro(stdscr, fila + 2, 0, f"Segmentos: {texto or '-'}")

    def render_detalle_fds(self, stdscr, fila, proceso, verbose):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "FDs todavía no disponibles")
            return

        fds = proceso.get("fds", [])
        limite = len(fds) if verbose else min(6, len(fds))
        self.addstr_seguro(
            stdscr, fila, 0,
            f"Total FDs: {proceso.get('total_fds', 0)} | "
            f"tipos: {proceso.get('fds_por_tipo', {})}",
        )
        for indice, fd in enumerate(fds[:limite], start=1):
            self.addstr_seguro(
                stdscr, fila + indice, 0,
                f"fd {fd['fd']:>3} [{fd['tipo']}] -> {fd['destino']}",
            )

    def render_detalle_threads(self, stdscr, fila, proceso, verbose):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "Threads todavía no disponibles")
            return

        threads = proceso.get("threads", [])
        limite = len(threads) if verbose else min(6, len(threads))
        self.addstr_seguro(stdscr, fila, 0, f"Threads del proceso: {len(threads)}")
        for indice, thread in enumerate(threads[:limite], start=1):
            self.addstr_seguro(
                stdscr, fila + indice, 0,
                f"TID={thread['tid']} S={thread['estado']} "
                f"CPU={thread.get('cpu_percent', 0):.2f}% "
                f"ctx={thread.get('voluntary_ctxt_switches', 0)}/"
                f"{thread.get('nonvoluntary_ctxt_switches', 0)} "
                f"{thread['comm']}",
            )

    def render_detalle_senales(self, stdscr, fila, proceso):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "Señales todavía no disponibles")
            return

        campos = (
            ("Bloqueadas", "sigblk"),
            ("Ignoradas", "sigign"),
            ("Con handler", "sigcgt"),
            ("Pendientes proceso", "sigpnd"),
            ("Pendientes grupo", "shdpnd"),
        )
        for desplazamiento, (titulo, clave) in enumerate(campos):
            valores = ", ".join(proceso.get(clave, [])) or "-"
            self.addstr_seguro(stdscr, fila + desplazamiento, 0, f"{titulo}: {valores}")

    def render_detalle_scheduling(self, stdscr, fila, proceso):
        if not proceso:
            self.addstr_seguro(stdscr, fila, 0, "Scheduling todavía no disponible")
            return

        lineas = [
            f"nice={proceso.get('nice')} priority={proceso.get('priority')} "
            f"policy={proceso.get('policy')} rt_priority={proceso.get('rt_priority')}",
            f"affinity={proceso.get('cpu_affinity')} "
            f"SID={proceso.get('sid')} PGID={proceso.get('pgid')}",
            f"context switches: voluntary={proceso.get('voluntary_ctxt_switches')} "
            f"involuntary={proceso.get('nonvoluntary_ctxt_switches')}",
            f"utime={proceso.get('utime')} stime={proceso.get('stime')}",
        ]
        for desplazamiento, texto in enumerate(lineas):
            self.addstr_seguro(stdscr, fila + desplazamiento, 0, texto)

    def render_detalle_sistema(self, stdscr, fila, sistema):
        if not sistema:
            self.addstr_seguro(
                stdscr,
                fila,
                0,
                "Sistema todavía no disponible",
            )
            return

        cpu = sistema.get("cpu_percent", {})
        memoria = sistema.get("memoria", {})
        load = sistema.get("loadavg", {})

        btime = int(sistema.get("btime", 0))
        boot_time = (
            time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(btime),
            )
            if btime
            else "-"
        )

        lineas = [
            (
                f"CPU user={cpu.get('user', 0):.1f}% "
                f"system={cpu.get('system', 0):.1f}% "
                f"idle={cpu.get('idle', 0):.1f}% "
                f"iowait={cpu.get('iowait', 0):.1f}%"
            ),
            (
                f"Load: {load.get('load1', 0):.2f} "
                f"{load.get('load5', 0):.2f} "
                f"{load.get('load15', 0):.2f} | "
                f"uptime={sistema.get('uptime', {}).get('uptime', 0):.0f}s"
            ),
            f"Boot time: {boot_time}",
            (
                f"Procesos={sistema.get('procesos_totales', 0)} "
                f"threads={sistema.get('threads_totales', 0)} "
                f"zombies={sistema.get('zombies', 0)} "
                f"estados={sistema.get('procesos_por_estado', {})}"
            ),
            (
                f"Memoria total={memoria.get('MemTotal', 0) // 1024}MB "
                f"libre={memoria.get('MemFree', 0) // 1024}MB "
                f"buffers={memoria.get('Buffers', 0) // 1024}MB "
                f"cached={memoria.get('Cached', 0) // 1024}MB"
            ),
            (
                f"Swap total={memoria.get('SwapTotal', 0) // 1024}MB "
                f"libre={memoria.get('SwapFree', 0) // 1024}MB"
            ),
            "Top CPU: " + ", ".join(
                (
                    f"{proceso['pid']}:{proceso['nombre']}"
                    f"({proceso['cpu_percent']:.1f}%)"
                )
                for proceso in sistema.get("top_cpu", [])
            ),
            "Top MEM: " + ", ".join(
                (
                    f"{proceso['pid']}:{proceso['nombre']}"
                    f"({proceso['rss_bytes'] / (1024 * 1024):.1f}MB)"
                )
                for proceso in sistema.get("top_memoria", [])
            ),
        ]

        for desplazamiento, texto in enumerate(lineas):
            self.addstr_seguro(
                stdscr,
                fila + desplazamiento,
                0,
                texto,
            )

    def render_pantalla(self, stdscr):
        stdscr.erase()
        altura, ancho = stdscr.getmaxyx()
        filas_lista = max(3, min(10, altura // 2 - 3))
        procesos = self.obtener_procesos()
        pid = self.pid_activo(procesos)

        self.render_lista(stdscr, procesos, filas_lista)
        separador = 3 + filas_lista
        if separador < altura - 2:
            try:
                stdscr.hline(separador, 0, curses.ACS_HLINE, max(1, ancho - 1))
            except curses.error:
                pass

        fila_detalle = separador + 1
        self.addstr_seguro(
            stdscr,
            fila_detalle,
            0,
            f"--- DETALLE {self.vista_actual.upper()} | PID {pid if pid is not None else '-'} ---",
            curses.A_BOLD,
        )
        fila_detalle += 1

        verbose = bool(self.snapshot["estado_global"].get("verbose", False))
        if self.vista_actual == "sistema":
            self.render_detalle_sistema(stdscr, fila_detalle, self.cache_vista)
        else:
            detalle = self.buscar_por_pid(self.cache_vista, pid)
            if self.vista_actual == "resumen":
                detalle = next((p for p in procesos if p.get("pid") == pid), None)
                self.render_detalle_resumen(stdscr, fila_detalle, detalle)
            elif self.vista_actual == "memoria":
                self.render_detalle_memoria(stdscr, fila_detalle, detalle)
            elif self.vista_actual == "fds":
                self.render_detalle_fds(stdscr, fila_detalle, detalle, verbose)
            elif self.vista_actual == "threads":
                self.render_detalle_threads(stdscr, fila_detalle, detalle, verbose)
            elif self.vista_actual == "senales":
                self.render_detalle_senales(stdscr, fila_detalle, detalle)
            elif self.vista_actual == "scheduling":
                self.render_detalle_scheduling(stdscr, fila_detalle, detalle)

        estado = self.snapshot["estado_global"]
        evento = estado.get("ultimo_evento", "")
        pie = (
            "1-7 vistas | ↑↓ navegar | Enter pin | / comando | u usuario | "
            "c ordenar | +/- intervalo | h ayuda | q salir"
        )
        if evento:
            pie += f" | {evento}"
        self.addstr_seguro(stdscr, altura - 1, 0, pie, curses.A_REVERSE)
        stdscr.refresh()

    def render_ayuda(self, stdscr):
        stdscr.erase()
        lineas = [
            "=== AYUDA ===",
            "",
            "1-7 o r/m/f/t/s/p/g  Cambiar de vista",
            "Flechas arriba/abajo   Navegar por procesos",
            "Enter                 Fijar/liberar el PID seleccionado",
            "/                     Filtrar por comando",
            "u                     Filtrar por usuario",
            "c                     Ordenar por CPU/RSS/PID",
            "+ / -                 Ajustar intervalo de la vista",
            "h / ?                 Cerrar esta ayuda",
            "q                     Salir",
        ]
        for fila, texto in enumerate(lineas):
            atributo = curses.A_BOLD if fila == 0 else 0
            self.addstr_seguro(stdscr, fila, 0, texto, atributo)
        stdscr.refresh()

    def render_prompt(self, stdscr):
        stdscr.erase()
        titulo = "comando" if self.modo_entrada == "comando" else "usuario"
        self.addstr_seguro(stdscr, 0, 0, f"=== FILTRO POR {titulo.upper()} ===", curses.A_BOLD)
        self.addstr_seguro(stdscr, 2, 0, self.entrada_buffer)
        self.addstr_seguro(stdscr, 4, 0, "Enter aceptar | Esc cancelar | vacío elimina el filtro")
        stdscr.refresh()

    def procesar_tecla(self, ch, procesos):
        if ch == -1:
            return

        tecla = chr(ch).lower() if 0 <= ch <= 255 else ""

        if tecla == "q":
            self.running = False
            self.snapshot["estado_global"]["running"] = False
        elif tecla in self.VISTAS:
            self.vista_actual = self.VISTAS[tecla]
            self.indice_seleccionado = 0
            self.version_vista = -1
            self.forzar_render = True
        elif tecla in ("h", "?"):
            self.mostrar_ayuda = not self.mostrar_ayuda
            self.forzar_render = True
        elif tecla == "c":
            ordenes = ("cpu_percent", "rss_bytes", "pid")
            indice = (ordenes.index(self.ordenar_por) + 1) % len(ordenes)
            self.ordenar_por = ordenes[indice]
            self.forzar_render = True
        elif tecla == "/":
            self.modo_entrada = "comando"
            self.entrada_buffer = ""
            self.forzar_render = True
        elif tecla == "u":
            self.modo_entrada = "usuario"
            self.entrada_buffer = ""
            self.forzar_render = True
        elif tecla == "+":
            self.modificar_intervalo(0.5)
        elif tecla == "-":
            self.modificar_intervalo(-0.5)
        elif ch == curses.KEY_UP:
            self.indice_seleccionado = max(0, self.indice_seleccionado - 1)
            self.forzar_render = True
        elif ch == curses.KEY_DOWN:
            if procesos:
                self.indice_seleccionado = min(len(procesos) - 1, self.indice_seleccionado + 1)
            self.forzar_render = True
        elif ch in (10, 13, curses.KEY_ENTER) and procesos:
            pid = procesos[self.indice_seleccionado]["pid"]
            self.pid_pinned = None if self.pid_pinned == pid else pid
            self.snapshot["estado_global"]["pid_pinned"] = self.pid_pinned
            self.forzar_render = True

    def procesar_prompt(self, ch):
        if ch == -1:
            return
        if ch == 27:
            self.modo_entrada = None
            self.entrada_buffer = ""
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            self.entrada_buffer = self.entrada_buffer[:-1]
        elif ch in (10, 13, curses.KEY_ENTER):
            if self.modo_entrada == "comando":
                self.filtro_comando = self.entrada_buffer.strip()
            else:
                self.filtro_usuario = self.entrada_buffer.strip()
            self.modo_entrada = None
            self.entrada_buffer = ""
            self.indice_seleccionado = 0
        elif 32 <= ch <= 126:
            self.entrada_buffer += chr(ch)
        self.forzar_render = True

    def renderizar(self, stdscr):
        try:
            curses.curs_set(0)
        except curses.error:
            pass

        stdscr.keypad(True)
        stdscr.timeout(100)

        # Primer dibujo completo de la terminal.
        stdscr.clearok(True)

        while self.running and self.snapshot["estado_global"].get("running", True):
            estado = self.snapshot["estado_global"]
            self.sincronizar_configuracion(estado)

            if estado.get("redibujar", False):
                estado["redibujar"] = False
                stdscr.clearok(True)
                self.forzar_render = True

            self.actualizar_cache()
            procesos = self.obtener_procesos()

            if self.forzar_render:
                if self.modo_entrada:
                    self.render_prompt(stdscr)
                elif self.mostrar_ayuda:
                    self.render_ayuda(stdscr)
                else:
                    self.render_pantalla(stdscr)
                self.forzar_render = False

            ch = stdscr.getch()

            # Cuando Docker attach o la terminal cambian de tamaño,
            # forzamos un redibujado físico completo.
            if ch == curses.KEY_RESIZE:
                curses.update_lines_cols()
                stdscr.clearok(True)
                self.forzar_render = True
                continue

            if self.modo_entrada:
                self.procesar_prompt(ch)
            
            elif self.mostrar_ayuda:
                if ch in (ord("h"), ord("?")):
                    self.mostrar_ayuda = False
                    self.forzar_render = True

                elif ch == ord("q"):
                    self.running = False
                    self.snapshot["estado_global"]["running"] = False

            else:
                self.procesar_tecla(ch, procesos)


def iniciar_display(snapshot, intervalos):
    interfaz = DisplayTUI(snapshot, intervalos)
    curses.wrapper(interfaz.renderizar)