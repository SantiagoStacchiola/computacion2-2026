import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analizadores.fds import construir_fds  # noqa: E402
from analizadores.memoria import clasificar_segmento, construir_memoria  # noqa: E402
from analizadores.resumen import calcular_cpu_percent, construir_resumen  # noqa: E402
from analizadores.scheduling import construir_scheduling, traducir_policy  # noqa: E402
from analizadores.senales import construir_senales  # noqa: E402
from analizadores.sistema import construir_sistema  # noqa: E402
import analizadores.threads as threads_mod  # noqa: E402


def crear_snapshot(pid=None, utime=100, stime=50, rss=10, cpu_user=1000):
    pid = pid or os.getpid()
    return {
        "timestamp": 123.0,
        "cpu": {
            "user": cpu_user,
            "nice": 0,
            "system": 500,
            "idle": 3000,
            "iowait": 20,
            "irq": 0,
            "softirq": 0,
            "steal": 0,
        },
        "memoria": {
            "MemTotal": 100000,
            "MemFree": 50000,
            "Buffers": 1000,
            "Cached": 5000,
            "SwapTotal": 20000,
            "SwapFree": 19000,
        },
        "procesos": {
            pid: {
                "stat": {
                    "pid": pid,
                    "comm": "proceso test",
                    "state": "R",
                    "ppid": 1,
                    "pgid": pid,
                    "sid": pid,
                    "minflt": 11,
                    "cminflt": 2,
                    "majflt": 3,
                    "cmajflt": 1,
                    "utime": utime,
                    "stime": stime,
                    "priority": 20,
                    "nice": 0,
                    "num_threads": 2,
                    "vsize": 4096,
                    "rss": rss,
                    "rt_priority": 0,
                    "policy": 0,
                },
                "status": {
                    "Uid": f"{os.getuid()} {os.getuid()} {os.getuid()} {os.getuid()}",
                    "Gid": f"{os.getgid()} {os.getgid()} {os.getgid()} {os.getgid()}",
                    "Threads": "2",
                    "VmSize": "4096 kB",
                    "VmRSS": "1024 kB",
                    "VmData": "512 kB",
                    "VmStk": "132 kB",
                    "VmExe": "4 kB",
                    "VmLib": "100 kB",
                    "VmHWM": "1200 kB",
                    "VmSwap": "0 kB",
                    "SigBlk": "0000000000000002",
                    "SigIgn": "0000000000000000",
                    "SigCgt": "0000000000004000",
                    "SigPnd": "0000000000000000",
                    "ShdPnd": "0000000000000000",
                    "Cpus_allowed_list": "0-3",
                    "voluntary_ctxt_switches": "10",
                    "nonvoluntary_ctxt_switches": "4",
                },
                "cmdline": "python proceso_test.py",
            }
        },
    }


class TestResumen(unittest.TestCase):
    def test_calcular_cpu_percent(self):
        stat_anterior = {"utime": 10, "stime": 5}
        stat_actual = {"utime": 20, "stime": 10}
        cpu_anterior = {"user": 100, "system": 50, "idle": 850}
        cpu_actual = {"user": 150, "system": 70, "idle": 880}
        porcentaje = calcular_cpu_percent(
            stat_actual, stat_anterior, cpu_actual, cpu_anterior
        )
        self.assertAlmostEqual(porcentaje, 15.0)

    def test_construir_resumen(self):
        snapshot = crear_snapshot()
        resultado = construir_resumen(snapshot)
        self.assertEqual(len(resultado), 1)
        proceso = resultado[0]
        self.assertEqual(proceso["cmdline"], "python proceso_test.py")
        self.assertIn("uid", proceso)
        self.assertIn("gid", proceso)
        self.assertIn("rss_bytes", proceso)


class TestMemoria(unittest.TestCase):
    def test_clasificar_segmentos(self):
        self.assertEqual(
            clasificar_segmento({"path": "[heap]", "permisos": "rw-p"}), "heap"
        )
        self.assertEqual(
            clasificar_segmento({"path": "[stack]", "permisos": "rw-p"}), "stack"
        )
        self.assertEqual(
            clasificar_segmento({"path": "/bin/app", "permisos": "r-xp"}), "text"
        )
        self.assertEqual(
            clasificar_segmento({"path": "", "permisos": "rw-p"}), "data"
        )
        self.assertEqual(
            clasificar_segmento({"path": "/tmp/a", "permisos": "rw-s"}), "shared"
        )

    @patch("analizadores.memoria.leer_maps")
    def test_construir_memoria(self, mock_maps):
        mock_maps.return_value = [
            {"path": "[heap]", "permisos": "rw-p", "tamano": 100},
            {"path": "/bin/app", "permisos": "r-xp", "tamano": 200},
        ]
        resultado = construir_memoria(crear_snapshot())
        proceso = resultado[0]
        self.assertEqual(proceso["faults"]["minor_faults"], 11)
        self.assertEqual(proceso["faults"]["major_faults"], 3)
        self.assertEqual(proceso["segmentos_agrupados"]["heap"]["tamano"], 100)
        self.assertEqual(proceso["segmentos_agrupados"]["text"]["tamano"], 200)


class TestFds(unittest.TestCase):
    @patch("analizadores.fds.leer_fds")
    def test_construir_fds(self, mock_fds):
        mock_fds.return_value = [
            {"fd": 0, "destino": "/dev/pts/0", "tipo": "tty"},
            {"fd": 3, "destino": "socket:[123]", "tipo": "socket"},
            {"fd": 4, "destino": "socket:[456]", "tipo": "socket"},
        ]
        resultado = construir_fds(crear_snapshot())
        proceso = resultado[0]
        self.assertEqual(proceso["total_fds"], 3)
        self.assertEqual(proceso["fds_por_tipo"]["socket"], 2)
        self.assertEqual(proceso["fds_por_tipo"]["tty"], 1)


class TestSenales(unittest.TestCase):
    def test_construir_senales(self):
        resultado = construir_senales(crear_snapshot())
        proceso = resultado[0]
        self.assertIn("SIGINT", proceso["sigblk"])
        self.assertIn("SIGTERM", proceso["sigcgt"])
        self.assertEqual(proceso["sigpnd"], [])


class TestScheduling(unittest.TestCase):
    def test_traducir_policy(self):
        self.assertEqual(traducir_policy(0), "OTHER")
        self.assertEqual(traducir_policy(1), "FIFO")
        self.assertEqual(traducir_policy(2), "RR")
        self.assertEqual(traducir_policy(999), "UNKNOWN(999)")

    def test_construir_scheduling(self):
        resultado = construir_scheduling(crear_snapshot())
        proceso = resultado[0]
        self.assertEqual(proceso["policy"], "OTHER")
        self.assertEqual(proceso["cpu_affinity"], "0-3")
        self.assertEqual(proceso["voluntary_ctxt_switches"], 10)
        self.assertEqual(proceso["nonvoluntary_ctxt_switches"], 4)


class TestThreads(unittest.TestCase):
    def setUp(self):
        threads_mod._historial_threads = {}
        threads_mod._cpu_anterior = None

    @patch("analizadores.threads.leer_threads")
    def test_cpu_de_thread_entre_dos_muestras(self, mock_threads):
        pid = os.getpid()
        mock_threads.return_value = [
            {
                "tid": pid,
                "comm": "main",
                "estado": "R",
                "utime": 10,
                "stime": 5,
                "voluntary_ctxt_switches": 2,
                "nonvoluntary_ctxt_switches": 1,
            }
        ]
        primera = crear_snapshot(pid=pid, cpu_user=1000)
        resultado1 = threads_mod.construir_threads(primera)
        self.assertEqual(resultado1[0]["threads"][0]["cpu_percent"], 0.0)

        mock_threads.return_value = [
            {
                "tid": pid,
                "comm": "main",
                "estado": "R",
                "utime": 20,
                "stime": 5,
                "voluntary_ctxt_switches": 3,
                "nonvoluntary_ctxt_switches": 1,
            }
        ]
        segunda = crear_snapshot(pid=pid, cpu_user=1100)
        resultado2 = threads_mod.construir_threads(segunda)
        cpu_thread = resultado2[0]["threads"][0]["cpu_percent"]
        self.assertGreater(cpu_thread, 0.0)


class TestSistema(unittest.TestCase):
    @patch("analizadores.sistema.leer_btime", return_value=100)
    @patch(
        "analizadores.sistema.leer_uptime",
        return_value={"uptime": 200.0, "idle_time": 100.0},
    )
    @patch(
        "analizadores.sistema.leer_loadavg",
        return_value={
            "load1": 0.1,
            "load5": 0.2,
            "load15": 0.3,
            "procesos_corriendo": 1,
            "procesos_totales": 10,
            "ultimo_pid": 99,
        },
    )
    def test_construir_sistema(self, _load, _uptime, _btime):
        anterior = crear_snapshot(utime=90, stime=45, cpu_user=900)
        actual = crear_snapshot(utime=100, stime=50, cpu_user=1000)
        resultado = construir_sistema(actual, anterior)
        self.assertEqual(resultado["procesos_totales"], 1)
        self.assertEqual(resultado["threads_totales"], 2)
        self.assertEqual(len(resultado["top_cpu"]), 1)
        self.assertEqual(len(resultado["top_memoria"]), 1)
        self.assertEqual(resultado["btime"], 100)
        self.assertIn("user", resultado["cpu_percent"])


if __name__ == "__main__":
    unittest.main()