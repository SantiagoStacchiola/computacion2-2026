import os
import signal
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from procfs import (  # noqa: E402
    PAGE_SIZE,
    decodificar_señales,
    extraer_cambios_de_contexto,
    extraer_memoria_de_status,
    leer_cmdline,
    leer_fds,
    leer_maps,
    leer_stat,
    leer_status,
    leer_threads,
    nombre_senal,
    rss_a_bytes,
)


class TestProcfsHelpers(unittest.TestCase):
    def test_rss_a_bytes(self):
        self.assertEqual(rss_a_bytes(3), 3 * PAGE_SIZE)

    def test_extraer_memoria_de_status(self):
        status = {
            "VmSize": "1000 kB",
            "VmRSS": "250 kB",
            "VmSwap": "5 kB",
        }
        memoria = extraer_memoria_de_status(status)
        self.assertEqual(memoria["VmSize"], 1000)
        self.assertEqual(memoria["VmRSS"], 250)
        self.assertEqual(memoria["VmSwap"], 5)
        self.assertEqual(memoria["VmData"], 0)

    def test_extraer_context_switches(self):
        status = {
            "voluntary_ctxt_switches": "12",
            "nonvoluntary_ctxt_switches": "7",
        }
        cambios = extraer_cambios_de_contexto(status)
        self.assertEqual(cambios["voluntary_ctxt_switches"], 12)
        self.assertEqual(cambios["nonvoluntary_ctxt_switches"], 7)

    def test_decodificar_senales(self):
        mascara = (1 << (signal.SIGINT - 1)) | (1 << (signal.SIGTERM - 1))
        nombres = decodificar_señales(f"{mascara:016x}")
        self.assertIn("SIGINT", nombres)
        self.assertIn("SIGTERM", nombres)

    def test_nombre_senal(self):
        self.assertEqual(nombre_senal(signal.SIGINT), "SIGINT")


class TestProcfsReal(unittest.TestCase):
    """Pruebas de integración livianas sobre el propio proceso de tests."""

    def setUp(self):
        self.pid = os.getpid()

    def test_leer_stat_y_status_del_propio_proceso(self):
        stat = leer_stat(self.pid)
        status = leer_status(self.pid)
        self.assertEqual(stat["pid"], self.pid)
        self.assertIn(stat["state"], {"R", "S", "D", "T", "t", "Z", "X", "I"})
        self.assertIn("Uid", status)
        self.assertIn("Gid", status)
        self.assertIn("Threads", status)

    def test_leer_cmdline(self):
        cmdline = leer_cmdline(self.pid)
        self.assertIsInstance(cmdline, str)

    def test_leer_maps(self):
        mapas = leer_maps(self.pid)
        self.assertIsInstance(mapas, list)
        self.assertGreater(len(mapas), 0)
        self.assertIn("permisos", mapas[0])
        self.assertIn("tamano", mapas[0])

    def test_leer_fds(self):
        fds = leer_fds(self.pid)
        self.assertIsInstance(fds, list)
        for fd in fds:
            self.assertIn("fd", fd)
            self.assertIn("destino", fd)
            self.assertIn("tipo", fd)

    def test_leer_threads(self):
        threads = leer_threads(self.pid)
        self.assertGreaterEqual(len(threads), 1)
        tids = {thread["tid"] for thread in threads}
        self.assertIn(self.pid, tids)
        for thread in threads:
            self.assertIn("voluntary_ctxt_switches", thread)
            self.assertIn("nonvoluntary_ctxt_switches", thread)


if __name__ == "__main__":
    unittest.main()