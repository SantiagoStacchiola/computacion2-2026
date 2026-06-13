# src/display.py

import curses
import time
import sys


class DisplayTUI:
    """
    Interfaz de usuario basada en curses.
    """
    
    VISTAS = {
        "1": "resumen",
        "2": "memoria",
        "3": "fds",
        "4": "threads",
        "5": "scheduling",
        "6": "senales",
        "7": "sistema",
        "r": "resumen",
        "m": "memoria",
        "f": "fds",
        "t": "threads",
        "s": "senales",
        "p": "scheduling",
        "g": "sistema",
    }
    
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.vista_actual = "resumen"
        self.scroll_pos = 0
        self.running = True
    
    def render_resumen(self, stdscr, data):
        """Renderiza la vista Resumen."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== RESUMEN ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        # Header
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'CPU%':8} {'RSS(MB)':10} {'THREADS':8}")
        
        # Procesos ordenados por CPU
        procesos = sorted(data, key=lambda p: p.get("cpu_percent", 0), reverse=True)
        for idx, p in enumerate(procesos[self.scroll_pos:self.scroll_pos+20]):
            linea = f"{p['pid']:6} {p['nombre']:20} {p.get('cpu_percent', 0):8.2f} "
            rss_mb = p.get('rss_bytes', 0) / (1024*1024)
            linea += f"{rss_mb:10.2f} {p.get('threads', 0):8}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_memoria(self, stdscr, data):
        """Renderiza la vista Memoria."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== MEMORIA ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'VmRSS(KB)':12} {'FAULTS':10}")
        
        procesos = sorted(data, key=lambda p: p.get('memoria_campos', {}).get('VmRSS', 0), reverse=True)
        for idx, p in enumerate(procesos[self.scroll_pos:self.scroll_pos+20]):
            vmrss = p.get('memoria_campos', {}).get('VmRSS', 0)
            faults = p.get('faults', {})
            minor = faults.get('minor_faults', 0)
            linea = f"{p['pid']:6} {p['nombre']:20} {vmrss:12} {minor:10}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_fds(self, stdscr, data):
        """Renderiza la vista FDs."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== FILE DESCRIPTORS ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'FDs':6} {'TIPOS'}")
        
        procesos = sorted(data, key=lambda p: p.get('total_fds', 0), reverse=True)
        for idx, p in enumerate(procesos[self.scroll_pos:self.scroll_pos+20]):
            tipos = p.get('fds_por_tipo', {})
            tipos_str = ", ".join([f"{k}:{v}" for k, v in list(tipos.items())[:3]])
            linea = f"{p['pid']:6} {p['nombre']:20} {p['total_fds']:6} {tipos_str}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_threads(self, stdscr, data):
        """Renderiza la vista Threads."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== THREADS ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'THREADS':8}")
        
        procesos = sorted(data, key=lambda p: p.get('num_threads', 0), reverse=True)
        for idx, p in enumerate(procesos[self.scroll_pos:self.scroll_pos+20]):
            linea = f"{p['pid']:6} {p['nombre']:20} {p['num_threads']:8}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_scheduling(self, stdscr, data):
        """Renderiza la vista Scheduling."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== SCHEDULING ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'NICE':6} {'POLICY'}")
        
        procesos = sorted(data, key=lambda p: p.get('nice', 0))
        for idx, p in enumerate(procesos[self.scroll_pos:self.scroll_pos+20]):
            linea = f"{p['pid']:6} {p['nombre']:20} {p['nice']:6} {p['policy']}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_senales(self, stdscr, data):
        """Renderiza la vista Señales."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== SEÑALES ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        stdscr.addstr(2, 0, f"{'PID':6} {'NOMBRE':20} {'SigCgt'}")
        
        con_senales = [p for p in data if p.get('sigcgt')]
        for idx, p in enumerate(con_senales[self.scroll_pos:self.scroll_pos+20]):
            senales_str = ",".join(p.get('sigcgt', [])[:3])
            linea = f"{p['pid']:6} {p['nombre']:20} {senales_str}"
            
            try:
                stdscr.addstr(3 + idx, 0, linea)
            except curses.error:
                pass
    
    def render_sistema(self, stdscr, data):
        """Renderiza la vista Sistema."""
        stdscr.clear()
        stdscr.addstr(0, 0, "=== SISTEMA ===", curses.A_BOLD)
        
        if not data:
            stdscr.addstr(2, 0, "Cargando...")
            return
        
        sistema = data[0] if isinstance(data, list) else data
        
        linea = 2
        stdscr.addstr(linea, 0, f"Procesos: {sistema.get('procesos_totales', 0)}")
        linea += 1
        
        stdscr.addstr(linea, 0, f"Threads totales: {sistema.get('threads_totales', 0)}")
        linea += 1
        
        cpu = sistema.get('cpu_percent', {})
        stdscr.addstr(linea, 0, f"CPU: User={cpu.get('user', 0):.1f}% Sys={cpu.get('system', 0):.1f}% Idle={cpu.get('idle', 0):.1f}%")
        linea += 1
        
        load = sistema.get('loadavg', {})
        stdscr.addstr(linea, 0, f"Load: {load.get('load1', 0):.2f} {load.get('load5', 0):.2f} {load.get('load15', 0):.2f}")
        linea += 1
        
        mem = sistema.get('memoria', {})
        mem_total = mem.get('MemTotal', 0) // 1024
        mem_free = mem.get('MemFree', 0) // 1024
        stdscr.addstr(linea, 0, f"Memoria: {mem_total - mem_free}MB / {mem_total}MB")
    
    def renderizar(self, stdscr):
        """Renderiza la vista activa."""
        curses.curs_set(0)  # Ocultar cursor
        stdscr.nodelay(True)  # No bloquear en getch()
        stdscr.timeout(100)   # Timeout de 100ms
        
        while self.running:
            try:
                # Obtener datos de la vista actual
                vista_data = self.snapshot[self.vista_actual]["data"]
                
                # Renderizar según la vista activa
                if self.vista_actual == "resumen":
                    self.render_resumen(stdscr, vista_data)
                elif self.vista_actual == "memoria":
                    self.render_memoria(stdscr, vista_data)
                elif self.vista_actual == "fds":
                    self.render_fds(stdscr, vista_data)
                elif self.vista_actual == "threads":
                    self.render_threads(stdscr, vista_data)
                elif self.vista_actual == "scheduling":
                    self.render_scheduling(stdscr, vista_data)
                elif self.vista_actual == "senales":
                    self.render_senales(stdscr, vista_data)
                elif self.vista_actual == "sistema":
                    self.render_sistema(stdscr, vista_data)
                
                # Mostrar pie de página
                altura, ancho = stdscr.getmaxyx()
                pie = f"Vista: {self.vista_actual} (1-7) | q=salir | ↑↓=navegar | +/-=intervalo"
                try:
                    stdscr.addstr(altura - 1, 0, pie[:ancho], curses.A_REVERSE)
                except curses.error:
                    pass
                
                stdscr.refresh()
                
                # Procesar input
                try:
                    ch = stdscr.getch()
                    if ch == ord('q'):
                        self.running = False
                        self.snapshot["estado_global"]["running"] = False
                    elif chr(ch) in self.VISTAS:
                        self.vista_actual = self.VISTAS[chr(ch)]
                        self.scroll_pos = 0
                    elif ch == curses.KEY_UP:
                        self.scroll_pos = max(0, self.scroll_pos - 1)
                    elif ch == curses.KEY_DOWN:
                        self.scroll_pos += 1
                    elif ch == ord('+'):
                        vista = self.snapshot[self.vista_actual]
                        vista["intervalo"] = min(30, vista["intervalo"] + 1)
                        self.snapshot[self.vista_actual] = vista
                    elif ch == ord('-'):
                        vista = self.snapshot[self.vista_actual]
                        intervalo_min = {"resumen": 0.5, "memoria": 1, "fds": 2, 
                                        "threads": 0.5, "senales": 5, "scheduling": 5, "sistema": 1}
                        vista["intervalo"] = max(intervalo_min.get(self.vista_actual, 0.5), vista["intervalo"] - 1)
                        self.snapshot[self.vista_actual] = vista
                except:
                    pass
                
                time.sleep(0.1)
                
            except Exception as e:
                stdscr.addstr(0, 0, f"Error: {str(e)[:50]}")
                stdscr.refresh()
                time.sleep(0.5)


def iniciar_display(snapshot):
    """Punto de entrada para la TUI."""
    try:
        curses.wrapper(lambda stdscr: DisplayTUI(snapshot).renderizar(stdscr))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error en display: {e}")
    finally:
        snapshot["estado_global"]["running"] = False