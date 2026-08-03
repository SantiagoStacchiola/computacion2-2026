import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from manager import DEFAULT_INTERVALS, actualizar_vista


class TestManagerHelpers(unittest.TestCase):

    def test_intervalos_default(self):
        self.assertEqual(DEFAULT_INTERVALS["resumen"], 2.0)
        self.assertEqual(DEFAULT_INTERVALS["memoria"], 3.0)
        self.assertEqual(DEFAULT_INTERVALS["fds"], 5.0)
        self.assertEqual(DEFAULT_INTERVALS["threads"], 2.0)
        self.assertEqual(DEFAULT_INTERVALS["senales"], 10.0)
        self.assertEqual(DEFAULT_INTERVALS["scheduling"], 10.0)
        self.assertEqual(DEFAULT_INTERVALS["sistema"], 2.0)

    def test_actualizar_vista_incrementa_version(self):
        snapshot = {
            "resumen": {
                "data": [],
                "ts": 0.0,
                "version": 4,
            }
        }

        actualizar_vista(
            snapshot,
            "resumen",
            [{"pid": 123}],
            timestamp=50.0,
        )

        self.assertEqual(
            snapshot["resumen"]["data"],
            [{"pid": 123}],
        )
        self.assertEqual(
            snapshot["resumen"]["ts"],
            50.0,
        )
        self.assertEqual(
            snapshot["resumen"]["version"],
            5,
        )


if __name__ == "__main__":
    unittest.main()