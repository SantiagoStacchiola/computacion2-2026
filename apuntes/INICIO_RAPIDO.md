# Cómo abrir y ejecutar el TP2 desde cero

## 1. Copiar la carpeta

Extraé el ZIP. En **Visual Studio Code**: `Archivo > Abrir carpeta...` y elegí
`tp2-computacion`. No abras solo `main.py`: abrí la carpeta completa, porque
los archivos usan imports del paquete `app`.

## 2. Encender Docker

Iniciá Docker Desktop y esperá a que el motor Docker quede activo.

## 3. Iniciar el sistema

En VS Code, abrí `Terminal > Nueva terminal` y escribí:

```powershell
docker compose up --build
```

Si el terminal muestra mensajes de Uvicorn indicando que la aplicación arrancó,
abrí: **http://127.0.0.1:8000/docs**.

## 4. Probar una tarea sin escribir código

1. En Swagger, buscá **POST /tareas** y hacé clic en `Try it out`.
2. Reemplazá el JSON por este:

```json
{
  "tipo": "esperar",
  "parametros": {"segundos": 10},
  "timeout": 20
}
```

3. Presioná `Execute`: debe devolver **202** con un `id`.
4. Buscá **GET /tareas/{id_tarea}**, poné ese ID y consultá el estado.
5. Si todavía está trabajando, probá **DELETE /tareas/{id_tarea}**.
6. Abrí **GET /estadisticas** y mirá el resumen.

## 5. Ejecutar el benchmark en tu computadora

En **otra terminal** de VS Code (dejando Docker corriendo):

```powershell
py -m pip install -r requirements-dev.txt
py benchmarks/mediciones.py --base-url http://127.0.0.1:8000
```

Si el comando `py` no existe, usá `python`. El resultado se guarda en
`resultados_mediciones.json`. Los tiempos dependen de tu hardware.

En `README.md` reemplazá los números de referencia por los tuyos e indicá el
hardware, fecha, cantidad de workers y condiciones de la prueba.

## 6. Probar el código automáticamente

```powershell
py -m pytest -q
```

Los tests usan Python local, no necesitan Docker. Deberías ver **9 passed** si
todas las dependencias están bien instaladas y los puertos locales están
permitidos.

## 7. Verificar el apagado ordenado

Volvé a la terminal de Docker y pulsá `Ctrl+C`. Se escribirá un archivo
`volcados/estado_XXXXXXXX.json` que contiene las tareas de esa ejecución.

## 8. Subir el proyecto a GitHub

Creá un repositorio público, por ejemplo `tp2-computacion`, sin generar un
README desde GitHub porque el proyecto ya lo tiene. Luego, en VS Code:

```powershell
git init
git add .
git commit -m "TP2 plataforma de tareas distribuidas"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/tp2-computacion.git
git push -u origin main
```

Reemplazá `TU_USUARIO` por tu usuario real. No publiques claves ni tokens.

**Importante:** no se comprobó Docker Desktop ni GitHub desde este entorno;
corresponde validar el arranque y la subida en tu computadora.
