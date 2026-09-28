import threading
import time

def loop_infinito(label):
    while True:
        print(f"[{label}] trabajando...")
        time.sleep(1)

# Versión sin daemon (descomentar para probar, terminar con Ctrl+C)
#h = threading.Thread(target=loop_infinito, args=("no-daemon",))
#h.start()
#time.sleep(3)
#print("Main terminó pero el programa sigue vivo")

# Versión con daemon
h = threading.Thread(target=loop_infinito, args=("daemon",), daemon=True)
h.start()

time.sleep(3)
print("Main terminó: el daemon muere automáticamente")