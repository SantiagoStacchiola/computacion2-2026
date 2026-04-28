#!/usr/bin/env python3
"""Rate limiter usando señales."""
import signal
import time

class RateLimiter:
    def __init__(self, max_ops):
        self.max_ops = max_ops
        self.tokens = max_ops

        signal.signal(signal.SIGALRM, self._recargar)
        signal.setitimer(signal.ITIMER_REAL, 1, 1)  # cada 1 segundo

    def _recargar(self, sig, frame):
        self.tokens = self.max_ops
        print(f"\n[RL] Tokens recargados: {self.tokens}")

    def permitir(self):
        if self.tokens > 0:
            self.tokens -= 1
            return True
        return False


rl = RateLimiter(5)

print("Probando rate limiter (máx 5 ops/seg)")

for i in range(20):
    if rl.permitir():
        print(f"Operación {i} OK")
    else:
        print(f"Operación {i} BLOQUEADA")

    time.sleep(0.2)