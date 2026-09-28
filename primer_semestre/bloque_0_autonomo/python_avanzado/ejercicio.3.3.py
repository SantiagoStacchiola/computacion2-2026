class BufferedReader:
    def __init__(self, path, buffer_size=8192):
        self.path = path
        self.buffer_size = buffer_size
        self.file = None

    def __enter__(self):
        self.file = open(self.path, "r", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.file:
            self.file.close()

    def __iter__(self):
        if self.file is None:
            self.file = open(self.path, "r", encoding="utf-8")
            cerrar_al_final = True
        else:
            cerrar_al_final = False

        resto = ""

        try:
            while True:
                chunk = self.file.read(self.buffer_size)
                if not chunk:
                    break

                datos = resto + chunk
                lineas = datos.split("\n")

                resto = lineas.pop()

                for linea in lineas:
                    yield linea

            if resto:
                yield resto

        finally:
            if cerrar_al_final and self.file:
                self.file.close()
                self.file = None

# Ejemplo como context manager
with BufferedReader("log.txt", buffer_size=10) as reader:
    for linea in reader:
        print(linea)