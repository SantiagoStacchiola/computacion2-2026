# Guía de estudio y defensa — TP2 Computación II

Esta guía sirve para que puedas **explicar el proyecto** antes de presentarlo.
No alcanza con memorizar: abrí el código y seguí cada flujo.

## 1. Los archivos, explicados en orden

**`app/models.py`** — Define el contrato de la API:
- `CrearTarea`: recibe `tipo`, `parametros` y `timeout`.
- `ParametrosDescargar` exige de 1 a 20 URLs HTTP(S).
- `ParametrosHashear` exige `texto` y un número entero de `iteraciones`.
- `ParametrosEsperar` exige duración en segundos.
- `Estado`: valores que puede tomar una tarea.
- `RegistroTarea`: guarda ID, tipo, fechas, estado, error, resultado y worker.
- Pydantic rechaza valores incorrectos antes de encolar (HTTP 422).

**`app/main.py`** — Es la puerta de entrada HTTP:
- `lifespan` crea el gestor al iniciar y lo apaga al detener el servidor.
- `POST /tareas` valida y encola, devuelve 202 inmediatamente.
- `GET /tareas` lista con filtro; `GET /tareas/{id}` consulta una.
- `DELETE /tareas/{id}` indica al gestor que la cancele.
- `GET /estadisticas` resume actividad.
- Las rutas `/experimentos/...` solo están activas en el entorno de prácticas.

**`app/manager.py`** — Es el núcleo del sistema:
- `ManagerTareas` conserva la cola y el diccionario `registros`.
- `iniciar()` crea workers y `ProcessPoolExecutor`.
- `encolar()` inserta el trabajo en RAM y en `asyncio.Queue`.
- `_worker()` recibe IDs con `await cola.get()` y espera la ejecución con timeout.
- `_resolver()` decide si debe descargar, esperar o hashear.
- `cancelar()` marca el estado, cancela corrutinas y avisa a CPU si corresponde.
- `detener()` drena tareas, solicita cancelación, cierra recursos y guarda JSON.

**`app/tasks.py`** — Contiene las operaciones reales:
- `esperar()` llama a `await asyncio.sleep()`, no bloquea el loop.
- `descargar()` usa `httpx.AsyncClient`, `asyncio.gather` y `async with`.
- `calcular_hash()` usa `hashlib.sha256` dentro de un `for` CPU-bound.
  Se ejecuta en **otro proceso**, no en el event loop.

**`Dockerfile`** — Construye un entorno Linux con Python 3.11, dependencias y
código; arranca Uvicorn con **una instancia**.

**`docker-compose.yml`** — Expone el puerto 8000 solo localmente, configura
`CANTIDAD_WORKERS=4`, `PROCESOS_CPU=2` y conserva `volcados/`.

**`tests/test_api.py`** — Comprueba rutas, estados, errores, timeout y
cancelaciones. **`benchmarks/mediciones.py`** — Reproduce los tres experimentos.

## 2. Ejemplo completo que podés contar oralmente

1. En Swagger (`/docs`) selecciono `POST /tareas` y mando una espera de 10 s.
2. FastAPI entrega los datos a Pydantic; Pydantic comprueba que son válidos.
3. `manager.encolar` crea un UUID, guarda un `RegistroTarea` como `pendiente` e
   inserta el ID en la `asyncio.Queue`.
4. La API devuelve **202** inmediatamente; todavía no necesitó esperar 10 s.
5. Un worker, que esperaba en `await cola.get()`, obtiene el ID y cambia estado
   a `ejecutando`.
6. El worker crea una corrutina para `esperar(10)` y usa `asyncio.wait_for`.
7. `asyncio.sleep(10)` deja libre el event loop; la API puede atender otros GET.
8. Al finalizar, el worker guarda resultado y estado `completada`, o `fallida`
   si hubo timeout, o `cancelada` si alguien envió DELETE.
9. `GET /tareas/{id}` devuelve el registro actualizado con las fechas.

## 3. Seis preguntas que el profesor anticipó

**¿Dónde podría bloquearse el event loop?**

En una función pesada llamada directamente desde un endpoint `async`, por
 ejemplo `calcular_hash(...)` en `/experimentos/bloqueo`. No existe un `await`
dentro del bucle CPU, por eso monopoliza el único hilo del event loop. La
implementación normal usa `loop.run_in_executor` en `manager._resolver`.

**¿Qué pasa si cancelo a mitad de una descarga?**

`manager.cancelar()` marca `cancelada` y llama `cancel()` a la corrutina en
curso. La cancelación se propaga por `asyncio.gather`, cancela las descargas
hijas y el `async with httpx.AsyncClient(...)` cierra recursos al salir.

**¿Por qué no necesita un Lock el pool?**

Porque los workers son corrutinas del **mismo event loop**. Los fragmentos
síncronos que cambian el estado, sin `await` dentro, se ejecutan sin que otra
corrutina se interponga. No significa que cualquier objeto compartido entre
threads/procesos no necesite sincronización.

**¿Qué se rompe primero si envío 10.000 tareas?**

Con `MAX_COLA=1000`, cuando las entradas no retiradas llegan al máximo,
`POST` devuelve 429 en lugar de permitir que crezca indefinidamente la cola.
La API tiene también coste de RAM por registros y resultados; no hay limpieza
automática del histórico. Si llegan 10.000 solicitudes distribuidas a lo largo
del tiempo, las aceptadas podrían superar 1.000 cuando los workers van retirando
entradas; el límite no es global.

**¿Qué diferencia hay entre `asyncio.gather` y `for` con `await` adentro?**

`for url in urls: await bajar(url)` espera a que la URL anterior termine antes
de iniciar la próxima. `await asyncio.gather(*(bajar(url) for url in urls))`
permite que todas progresen mientras esperan respuestas de red.

**¿Por qué `time.sleep()` en una corrutina es un bug?**

`time.sleep()` duerme el **hilo completo** del event loop y paraliza la API.
`await asyncio.sleep()` suspende solo esa corrutina y da oportunidad a las
otras tareas de ejecutarse.

## 4. Otras preguntas útiles

**¿Asincronismo equivale a paralelismo?** No. Las operaciones I/O pueden
solaparse en un hilo; el trabajo CPU de verdad se despacha a procesos distintos.

**¿Por qué no usar `requests`?** Porque su modelo habitual es bloqueante;
`httpx.AsyncClient` ofrece descargas asíncronas y encaja con el event loop.

**¿Por qué FastAPI devuelve 202 y no 200?** 202 Accepted señala que se aceptó
el trabajo para procesamiento pero todavía no se completó.

**¿Cómo se controla el timeout?** Con `asyncio.wait_for(corrutina, timeout=...)`.
Si vence, se cancela la tarea y se guarda error en `fallida`.

**¿Se puede detener automáticamente cualquier función CPU cancelando su
Future?** No. La cancelación del Future no mata un proceso en ejecución.
Se agregó un flag compartido que el hash revisa periódicamente.

**¿Por qué usar un solo proceso de Uvicorn?** Porque la lista de tareas y la
cola están guardadas en memoria local; dos servidores separados no compartirían
los mismos trabajos. Esto no es una cola intermáquinas como Redis/RabbitMQ.

**¿El apagado conserva información?** Sí, escribe `estado_*.json`. Al reiniciar
registra la existencia del archivo, pero no restaura los trabajos.

## 5. Qué ejecutar delante del profesor

1. `docker compose up --build` (servidor funcionando).
2. Abrir `/docs` y crear `esperar` de 10 segundos.
3. Consultar su ID y cancelarla con DELETE antes de que termine.
4. Crear `hashear` con 100000 iteraciones y consultar el resultado.
5. Crear `descargar` con dos URLs y mostrar tamaños/tiempos.
6. Consultar `/estadisticas` y filtrar `/tareas?estado=completada`.
7. Mostrar `pytest -q` y el script de `mediciones.py`.
8. Detener el servidor y revisar el nuevo archivo en `volcados/`.

**Antes de entregar:** repetir todas las mediciones en tu computadora;
comprobar Docker real, y comprender cada decisión. No digas que mediste un dato
en una máquina si en realidad proviene del entorno de referencia.
