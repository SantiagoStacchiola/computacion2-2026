# Trabajo Práctico N.º 2 — Plataforma de Tareas Distribuidas

**Computación II — Universidad de Mendoza — 2026**  
**Lenguaje:** Python 3.11+ · **API:** FastAPI · **Concurrencia:** `asyncio` · **Contenedores:** Docker Compose

## 1. Ejecución

### Requisitos

- Docker Desktop con el motor encendido (Windows/macOS), o Docker Engine y Compose (Linux).
- En una terminal, situarse en la carpeta que contiene `docker-compose.yml`.

```bash
docker compose up --build
```

API: <http://127.0.0.1:8000> · Swagger UI: <http://127.0.0.1:8000/docs>  
Detener ordenadamente con Ctrl+C, o desde otra terminal con `docker compose down`.
Al detenerse se escribe `volcados/estado_<timestamp>.json` (la carpeta está
montada como volumen, así que el archivo queda en el host).

### Opción sin Docker

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
# Linux/macOS:
HABILITAR_EXPERIMENTOS=1 uvicorn app.main:app --host 127.0.0.1 --port 8000
# Windows PowerShell: $env:HABILITAR_EXPERIMENTOS="1"; uvicorn app.main:app --host 127.0.0.1 --port 8000
```

No arrancar con múltiples workers de Uvicorn ni con `--reload` para las mediciones.

### Nota sobre plataformas (`spawn`, guarda `__main__` y señales)

- `ProcessPoolExecutor` arranca distinto según el sistema (`fork` en Linux,
  `spawn` en macOS y Windows). Para que el comportamiento sea idéntico en todos,
  `ManagerTareas.iniciar()` pide **explícitamente** el contexto `spawn`
  (`multiprocessing.get_context("spawn")`). Con `spawn` los procesos hijos
  re-importan el módulo, por eso la función `calcular_hash` vive a nivel de
  módulo (para poder serializarse) y `main.py` protege el arranque manual con
  `if __name__ == "__main__":`. El pool se crea dentro del `lifespan`, no al
  importar el módulo, así que no hay bucle de reimportación.
- No uso `loop.add_signal_handler()` (solo Unix): SIGINT y SIGTERM los captura
  **Uvicorn**, que dispara el cierre del `lifespan`; ahí corre `detener()`. Eso
  funciona igual en Linux, macOS y Windows.

## 2. Uso de los endpoints

| Método | Ruta | Acción |
|---|---|---|
| `POST` | `/tareas` | Encola y devuelve `202 Accepted` inmediatamente |
| `GET` | `/tareas` | Lista tareas; `?estado=pendiente` filtra |
| `GET` | `/tareas/{id}` | Obtiene estado, tiempos y resultado |
| `DELETE` | `/tareas/{id}` | Cancela una tarea pendiente o en ejecución |
| `GET` | `/estadisticas` | Totales por estado, tiempos promedio y workers ocupados |
| `GET` | `/salud` | Estado básico del proceso |

Los estados válidos son `pendiente`, `ejecutando`, `completada`, `fallida` y
`cancelada`. En los ejemplos se usa `curl` (en PowerShell puede ser necesario
escribir `curl.exe`).

**Ejemplo A: simular una espera**

```bash
curl -X POST http://127.0.0.1:8000/tareas \
  -H "Content-Type: application/json" \
  -d '{"tipo":"esperar","parametros":{"segundos":10},"timeout":20}'
```

La respuesta incluye un `id` UUID. El estado inicial es `pendiente`, aunque
puede pasar rápidamente a `ejecutando`. Reemplazar `ID` con el identificador:

```bash
curl http://127.0.0.1:8000/tareas/ID
curl "http://127.0.0.1:8000/tareas?estado=ejecutando"
curl -X DELETE http://127.0.0.1:8000/tareas/ID
curl http://127.0.0.1:8000/estadisticas
```

**Ejemplo B: hashear un texto en otro proceso**

```bash
curl -X POST http://127.0.0.1:8000/tareas \
  -H "Content-Type: application/json" \
  -d '{"tipo":"hashear","parametros":{"texto":"hola mundo","iteraciones":500000},"timeout":30}'
```

**Ejemplo C: descargar URLs concurrentemente**

```bash
curl -X POST http://127.0.0.1:8000/tareas \
  -H "Content-Type: application/json" \
  -d '{"tipo":"descargar","parametros":{"urls":["https://example.com/","https://www.python.org/"],"modo":"concurrente"},"timeout":30}'
```

Cada URL produce su código de estado, tamaño en bytes, duración y error (si
hubiera). El modo normal es `concurrente`; `secuencial` existe solamente para
comparar las mismas descargas en el experimento. Las URL de terceros requieren
Internet; para los experimentos se usa un endpoint local propio.

**Ejemplo D: timeout.** Una espera de 10 s con `"timeout":0.5` pasa a `fallida`
con el motivo `Timeout de 0.5 segundos superado`:

```bash
curl -X POST http://127.0.0.1:8000/tareas \
  -H "Content-Type: application/json" \
  -d '{"tipo":"esperar","parametros":{"segundos":10},"timeout":0.5}'
```

**Ejemplo E: filtrar por estado y ver estadísticas**

```bash
curl "http://127.0.0.1:8000/tareas?estado=fallida"
curl http://127.0.0.1:8000/estadisticas
```

## 3. Arquitectura y flujo de una tarea

```text
                    solicitud POST /tareas
                             |
                             v
                     +-----------------+
     GET /tareas <---| API FastAPI     |---> GET /estadisticas
                     +--------+--------+
                              | valida + crea UUID, respuesta 202
                              v
                     +-----------------+
                     | Registro en RAM |<-----+ estado/resultado
                     +--------+--------+      |
                              |               |
                              v               |
                     +-----------------+      |
                     | asyncio.Queue   |      |
                     +--------+--------+      |
                              | await get()   |
                              v               |
                     +-----------------+      |
                     | N workers async |------+
                     +----+-------+----+
                          |       |
             I/O-bound    |       | CPU-bound
                    +-----v--+ +--v-------------------+
                    | httpx  | | ProcessPoolExecutor |
                    | sleep  | | SHA-256 en procesos |
                    +--------+ +----------------------+
```

**Secuencia:** la API valida los parámetros con Pydantic, registra la tarea y
hace `put_nowait` sobre `asyncio.Queue`. No espera a la ejecución. Un worker
consume con `await cola.get()`, marca `ejecutando` y delega el trabajo a la
corrutina correspondiente, limitada por `asyncio.wait_for`. Registra el
resultado o el error, marca el estado final y llama a `cola.task_done()`.

Los módulos son:

- `app/models.py`: esquemas de validación, identificadores y estados.
- `app/main.py`: FastAPI, endpoints y ciclo de vida (`lifespan`).
- `app/manager.py`: pool, cola, cancelación, métricas, volcado y procesos CPU.
- `app/tasks.py`: tareas concretas de descarga, hash y espera.
- `benchmarks/mediciones.py`: las tres mediciones obligatorias, reproducibles.
- `benchmarks/techo_pool.py`: medición 3 con cargas grandes (100 a 10.000 tareas).
- `tests/test_api.py`: pruebas automatizadas con `pytest`.

## 4. Decisiones de diseño

### 4.1 ¿Por qué `asyncio.Queue` y no `queue.Queue`?

`asyncio.Queue.get()` espera con `await` y libera el event loop: mientras un
worker espera un trabajo, el servidor responde a otros clientes. `queue.Queue`
bloquea el hilo con operaciones pensadas para threads; llamada desde una
corrutina congelaría **todo** el event loop. Como los workers son corrutinas
sobre un mismo loop, `asyncio.Queue` es el mecanismo apropiado.

Además, la cola tiene `maxsize` (`MAX_COLA`, 1000 por defecto): si se llena,
`POST /tareas` responde 429. Es *backpressure* elemental.

### 4.2 ¿Cómo evito que una tarea CPU-bound congele la API?

`asyncio` evita bloquear cuando una corrutina **espera I/O**; no hace paralela
una función que ocupa CPU de forma continua. Si `calcular_hash()` se llama
directamente dentro de una corrutina, no hay ningún `await` donde el loop pueda
ceder y todas las conexiones quedan esperando.

La solución es `loop.run_in_executor(ProcessPoolExecutor, calcular_hash, ...)`:
el hash corre en **otro proceso** y la corrutina del worker solo espera el
`Future` con `await`, cediendo el loop. Elegí **procesos y no threads** porque
un thread que ejecuta bytecode Python compite por el GIL con el event loop;
además `hashlib` solo libera el GIL con entradas grandes, y acá el texto de
entrada es chico (el costo está en las iteraciones). Un proceso aparte no
comparte GIL y puede usar otro núcleo.

Para demostrarlo existe `/experimentos/bloqueo` (solo con
`HABILITAR_EXPERIMENTOS=1`), que llama a la misma función **directamente** en
el endpoint. Es deliberadamente incorrecto y no debe exponerse públicamente.

### 4.3 ¿Cómo implementé la cancelación y qué pasa con los recursos a medio usar?

- **Pendiente:** pasa a `cancelada`; cuando un worker retira su ID de la cola,
  lo descarta sin ejecutarla.
- **Descargando:** `cancel()` sobre la tarea. El `CancelledError` se propaga por
  `asyncio.gather` a las descargas hijas, y los `async with` (`cliente.stream` y
  `httpx.AsyncClient`) cierran las conexiones al salir. No quedan corrutinas
  huérfanas ni sockets abiertos.
- **Esperando:** `asyncio.sleep()` termina al recibir `CancelledError`.
- **Hasheando:** cancelar el `await` **no detiene** un proceso que ya está
  calculando. Por eso se pasa una señal compartida
  (`multiprocessing.Manager().Event()`) que `calcular_hash` revisa cada 1024
  iteraciones; al activarse, el proceso corta solo y queda libre para otras
  tareas. El `asyncio.shield` evita que cancelar el `await` destruya el `Future`
  interno antes de que el proceso reaccione.
- **Timeout:** `asyncio.wait_for()` cancela la ejecución y el registro termina en
  `fallida` con el motivo.

La API devuelve `cancelada` apenas se acepta la orden; la liberación interna del
executor puede completarse unos instantes después. Los estados terminales no se
sobrescriben cuando regresan los resultados. En el bloque `finally` del worker
se descuenta `ocupados`, se registra `finalizado_en` y se llama a `task_done()`
pase lo que pase.

### 4.4 ¿Qué pasa si un worker lanza una excepción no capturada?

Cada worker envuelve la ejecución en `try/except Exception`: marca la tarea
`fallida`, guarda `TipoDeExcepción: mensaje` y vuelve al bucle, así que **el
worker no muere** y el pool no se achica. `finally` libera el contador de
ocupación y llama a `cola.task_done()`. `CancelledError` se trata aparte porque
no es un error de negocio (en Python 3.8+ no hereda de `Exception`). Una
excepción en una URL de `descargar` ni siquiera llega al worker: se captura por
URL y el resto de las descargas se completa.

### 4.5 Apagado ordenado y persistencia

Uvicorn recibe SIGINT/SIGTERM y activa el cierre de `lifespan`. El gestor deja de
aceptar tareas (`POST` devuelve 503), espera con `cola.join()` hasta
`GRACIA_APAGADO` segundos y, si vence el plazo, cancela las pendientes o
activas. Luego cierra workers y pool y escribe
`volcados/estado_<timestamp>.json`. En el próximo arranque **registra por log**
el último volcado encontrado; no lo restaura (no se pidió). En Docker,
`stop_grace_period` (25 s) es mayor que `GRACIA_APAGADO` (10 s) para que Docker
no mate el proceso antes de terminar el volcado.

### 4.6 ¿Por qué `httpx` y no `aiohttp`?

La consigna prohíbe `requests` y pide justificar la librería asíncrona. Elegí
`httpx.AsyncClient` porque:

- Tiene una API casi idéntica a `requests`, lo que baja la curva de aprendizaje.
- Soporta *streaming* (`client.stream` + `aiter_bytes`), que uso para cortar
  respuestas de más de 5 MB.
- Trae `Timeout` y `Limits` (pool de conexiones) integrados y configurables.
- Es la misma librería que usan los tests (`ASGITransport`) y el benchmark, así
  que hay una sola dependencia HTTP.

Contrapartida: `aiohttp` suele rendir algo mejor con muchísimas conexiones
simultáneas y además trae servidor propio. Para el volumen de este TP (hasta 20
URL por tarea) la diferencia no es relevante.

## 5. Mediciones

### Cómo reproducirlas

Con el servidor levantado y las rutas experimentales habilitadas
(`HABILITAR_EXPERIMENTOS=1`, ya activo en `docker-compose.yml`):

```bash
pip install -r requirements-dev.txt
python benchmarks/mediciones.py --base-url http://127.0.0.1:8000
```

El script guarda `resultados_mediciones.json`. Mi corrida está copiada en
[`resultados_mediciones.json`](resultados_mediciones.json).

Para la medición 3 con cargas grandes (sección 5.3.1):

```bash
python benchmarks/techo_pool.py --niveles 100 500 1000 2000 5000 10000
```

Se corrió un nivel por vez, reiniciando el servidor entre niveles
(`docker compose restart api`) para que los registros viejos no distorsionen las
latencias. Los resultados están unidos en
[`techo_pool.json`](techo_pool.json).

### Entorno de la medición

| | |
|---|---|
| Fecha | 31/10/2026 |
| Sistema (cliente) | Linux sobre **WSL2** (kernel 6.6.87.2, x86_64) |
| Python (cliente) | 3.12.3 |
| Servidor | Docker (`python:3.11-slim`)  |
| CPU / núcleos / RAM | (Ryzen 5 5600H, 4 núcleos, 16 GB) |
| Configuración | `CANTIDAD_WORKERS=4`, `PROCESOS_CPU=2`, `MAX_COLA=1000` |
| Endpoint remoto simulado | `/experimentos/latencia` (`asyncio.sleep(0.2)`) |

Son números de **mi** máquina, con 2 repeticiones por modalidad. Dependen del
hardware y de WSL2, así que sirven para comparar las modalidades entre sí, no como
valores absolutos.

### 5.1 Concurrencia I/O: 20 descargas secuenciales vs. concurrentes

| Modalidad | Corrida 1 | Corrida 2 | Promedio |
|---|---:|---:|---:|
| Secuencial | 4,1523 s | 4,1187 s | **4,1355 s** |
| Concurrente | 0,2979 s | 0,3007 s | **0,2993 s** |

**Speedup:** `4,1355 / 0,2993 = 13,82×`.

**Interpretación:** en el `for` secuencial cada petición espera a la anterior y
los 20 retardos de 0,2 s se suman (20 × 0,2 = 4,0 s; el resto, ~0,13 s, es
overhead de red y de la propia tarea). Con `asyncio.gather` las 20 peticiones
esperan a la vez y el total se acerca al retardo de **una sola** (0,2 s). No llega
a 20× porque quedan ~0,1 s de costo fijo: abrir 20 conexiones TCP, la creación de
tareas y el *polling* de 25 ms del benchmark. Además el "servidor remoto" es el
mismo proceso Uvicorn, así que cliente y servidor comparten un event loop, lo que
suma algo de contención. Aun así, la espera de I/O se superpone casi por
completo: eso es lo que resuelve `asyncio`.

### 5.2 El event loop bloqueado: sin executor vs. con executor

Se ejecutaron **4.000.000 iteraciones** de SHA-256 y se midió cuánto tardaba en
responder un `GET /tareas` iniciado mientras el cálculo estaba en curso:

| Implementación | Latencia de `GET /tareas` |
|---|---:|
| Hash dentro del endpoint `async` (sin executor, incorrecto) | **2,3540 s** |
| Hash en `ProcessPoolExecutor` | **0,0044 s** |

Diferencia: `2,3540 / 0,0044 ≈ 535×`. El cálculo bloqueante duró en total 2,4571 s.

**Interpretación:** sin executor, el `GET` tardó prácticamente lo mismo que el
cálculo (2,35 s de 2,46 s): estuvo **esperando a que el loop se liberara**. Todo
cliente conectado habría sufrido la misma demora, y eso incluye las demás
tareas del pool, los timeouts y las cancelaciones, que también dependen del loop.
Con executor, el trabajo pesado corre en otro proceso y el loop sigue libre: el
`GET` responde en 4 ms. El 535× **no** significa que SHA-256 sea más rápido
(el cálculo tarda lo mismo en ambos casos); mejora la **capacidad de respuesta**
de la API. Es la diferencia entre concurrencia (alternar esperas) y paralelismo
(usar otro núcleo).

### 5.3 Techo del pool de workers

Tareas `esperar` de **0,4 s**, con `CANTIDAD_WORKERS=4`, todas enviadas a la vez:

| Tareas simultáneas | Tandas teóricas (⌈n/4⌉) | Tiempo teórico | Tiempo medido | Tareas/seg |
|---:|---:|---:|---:|---:|
| 1 | 1 | 0,4 s | 0,4280 s | 2,34 |
| 2 | 1 | 0,4 s | 0,4143 s | 4,83 |
| 4 | 1 | 0,4 s | 0,4293 s | 9,32 |
| 8 | 2 | 0,8 s | 0,8511 s | 9,40 |
| 16 | 4 | 1,6 s | 1,6761 s | 9,55 |
| 32 | 8 | 3,2 s | 3,2743 s | 9,77 |

**Interpretación:** hasta 4 tareas el tiempo es plano (~0,42 s): todas caben en la
primera tanda. A partir de 8 el tiempo crece linealmente con las tandas, y el
rendimiento se estanca en ≈ 9,4–9,8 tareas/s, muy cerca del máximo teórico
`4 workers / 0,4 s = 10 tareas/s`. **El límite está en el tamaño del pool, no en
`asyncio`**: el event loop podría tener miles de `sleep` simultáneos, pero solo 4
workers consumen de la cola, y el resto espera su turno en estado `pendiente`.
Para tareas `hashear` el techo sería distinto: lo fijarían los `PROCESOS_CPU=2`
(y los núcleos reales), no los workers.

#### 5.3.1 Más allá de 32 tareas: 100 a 10.000

Para llegar a miles de tareas sin esperar minutos, cada tarea `esperar` dura
**0,05 s** (en vez de 0,4 s); el máximo teórico pasa a ser `4 workers / 0,05 s =
80 tareas/s`. Cada fila es una corrida con las N tareas enviadas de golpe, con
100 `POST` simultáneos desde el cliente y `MAX_COLA=1000`. Las latencias de
`GET /estadisticas` se midieron **durante** el envío (promedio / máximo).

| Enviadas | Aceptadas (202) | Rechazadas (429) | Tiempo de envío | Tiempo total | Tareas/s | `GET /estadisticas` bajo carga (prom / máx) | `GET /tareas` al final |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 100 | 0 | 0,6 s | 1,4 s | 69,8 | 0,026 / 0,11 s | 0,006 s |
| 500 | 500 | 0 | 2,7 s | 6,7 s | 75,0 | 0,061 / 1,08 s | 0,016 s |
| 1.000 | 1.000 | 0 | 6,8 s | 13,2 s | 76,0 | 0,103 / 2,51 s | 0,035 s |
| 2.000 | 1.892 | 108 | 11,4 s | 24,7 s | 76,6 | 0,078 / 1,88 s | 0,024 s |
| 5.000 | 3.185 | 1.815 | 27,9 s | 41,6 s | 76,6 | 0,171 / 2,63 s | 0,043 s |
| 10.000 | 5.200 | 4.800 | 53,8 s | 67,8 s | 76,7 | 0,253 / 2,21 s | 0,049 s |

**Interpretación**

- **El techo de procesamiento son los workers.** El rendimiento se estabiliza en
  ≈ 76,6 tareas/s, un 96 % del máximo teórico de 80. Con 100 tareas da menos
  (69,8) porque el arranque y el *polling* pesan más sobre un total de 1,4 s. No
  hay degradación por tarea: el tiempo total crece linealmente con la cantidad
  aceptada (por ejemplo, 5.200 tareas ÷ 67,8 s = 76,7 tareas/s). Lo único que
  crece es la espera en la cola.
- **El límite de admisión es `MAX_COLA`.** Hasta 1.000 tareas no hubo ningún 429.
  Desde 2.000 aparecen, porque el cliente envía más rápido de lo que consumen los
  4 workers y la cola llega a 1.000 entradas sin retirar. La cantidad aceptada se
  explica casi exacto con `MAX_COLA + tasa de consumo × tiempo de envío`: para
  10.000 tareas, `1.000 + 76,7 × 53,8 s ≈ 5.130` (medido: 5.200). Es decir, los 429
  no dependen de N en sí, sino de cuánto tarda el cliente en enviar mientras los
  workers van vaciando la cola.
- **Lo que se degrada primero es la respuesta de la API, no los workers.** Con
  100 `POST` simultáneos el servidor procesó unos 190 `POST`/s (10.000 envíos en
  53,8 s), y `GET /estadisticas` pasó de unos pocos milisegundos (5 a 25 ms al
  terminar) a **entre 1 y 2,6 s en el peor caso** bajo carga. Los workers siguen consumiendo a ritmo constante, pero
  el único event loop tiene que validar, registrar y responder cada solicitud
  (también los 429), así que las demás consultas esperan su turno. El *backpressure*
  protege la cola, no el loop. Parte de esa latencia puede venir de que cliente y
  servidor compiten por los mismos 4 núcleos de WSL2.
- **Todas las tareas aceptadas terminaron** (`terminaron_todas: true` en todos los
  niveles): la API rechazó carga pero no perdió trabajo ni se cayó.
- **`GET /tareas` crece con la cantidad de registros**, ya que serializa todos: de
  5,6 ms con 100 registros a 48,6 ms con 5.200. A esta escala es tolerable, pero es
  lineal y confirma la limitación de falta de paginación (sección 8).
- **Memoria:** no se midió el consumo del contenedor; por diseño `registros` crece
  sin límite mientras el proceso viva.
- **Tareas `hashear`:** no se midió el techo con CPU-bound. Por diseño lo fijarían
  los `PROCESOS_CPU=2` (y los núcleos disponibles), no los 4 workers.

**Conclusión de la medición 3:** hay tres límites distintos y ocurren en este orden
al subir la carga: (1) a partir de 4 tareas simultáneas, el pool de 4 workers
(≈ 77 tareas/s para tareas de 50 ms); (2) a partir de unos 1.000 envíos rápidos,
la cola llena y los 429; (3) bajo envío masivo, el event loop saturado, que se nota
como latencia de segundos en las consultas.

## 6. Conceptos del curso aplicados

| Concepto / clases | Dónde está en el código y vínculo |
|---|---|
| Productor-consumidor (clase 11) | `encolar()` produce IDs con `put_nowait`; los N `_worker()` consumen con `await cola.get()`. Mismo patrón que con threads, pero con corrutinas: **no hace falta `Lock`** porque el event loop solo cambia de corrutina en un `await`, y entre registrar la tarea y `put_nowait` no hay ninguno. |
| Sockets TCP y servidores concurrentes (13–14) | Uvicorn atiende muchos clientes HTTP sobre sockets TCP en un solo hilo, sin un thread por conexión. `httpx` abre sockets TCP hacia cada URL descargada. |
| I/O multiplexing `select`/`epoll` (17) | Es lo que usa el event loop por debajo para saber qué sockets están listos. Por eso 20 descargas pueden esperar a la vez en un hilo (medición 5.1). |
| Generadores y corrutinas, `async`/`await` (18) | `esperar()`, `descargar()`, `_worker()` y los endpoints `async def` son corrutinas; cada `await` es un punto donde el loop puede cambiar de tarea. |
| HTTP y FastAPI (19) | Rutas en `main.py`, validación con Pydantic (422), códigos 202/404/429/503. |
| Asyncio en red y avanzado (20–21) | `asyncio.Queue`, `gather` en `descargar()`, `wait_for` para timeouts, `Task.cancel()` y `shield` para cancelar, `httpx.AsyncClient`. |
| `concurrent.futures` / executors (22) | `ProcessPoolExecutor` + `loop.run_in_executor` para `hashear`; flag compartido para cancelar el proceso. |
| Context managers (bloque 0) | `async with` para `AsyncClient` y `cliente.stream`; `@asynccontextmanager` en el `lifespan` (arranque y apagado). |
| Señales y apagado ordenado | SIGINT/SIGTERM los captura Uvicorn y disparan `detener()`. |

Un `for` con `await` adentro espera cada elemento antes de empezar el siguiente
(suma de tiempos); `gather` lanza todas las corrutinas y espera a que terminen
juntas (aprox. el tiempo de la más lenta). Es exactamente la diferencia medida
en 5.1: 4,14 s contra 0,30 s.

## 7. Preguntas de la corrección

**¿Dónde podría bloquear el event loop mi código?**
1. En `/experimentos/bloqueo`, a propósito (medición 5.2).
2. En las llamadas al proceso `Manager` que son **síncronas**:
   `mp_manager.Event()` (al iniciar un hash) y `senal.set()` (al cancelar). Son
   una ida y vuelta por IPC; normalmente tardan menos de un milisegundo, pero
   técnicamente bloquean el loop mientras esperan.
3. En trabajo proporcional a la cantidad de registros: `GET /tareas` y
   `/estadisticas` recorren y serializan todo `registros`, y `detener()` hace
   `json.dumps` del estado completo. Con decenas de miles de tareas se notaría.

**¿Qué pasa si cancelo una tarea justo a mitad de una descarga?**
`DELETE` marca la tarea `cancelada` y llama a `Task.cancel()`. El `CancelledError`
sale por el `await` de `httpx` que esté en curso, `gather` cancela las otras
descargas, y los `async with` cierran las conexiones. El worker captura la
cancelación, deja el estado `cancelada` (no lo pisa), descuenta `ocupados` y vuelve
a la cola. Hay un test para esto (`test_cancelar_descarga_en_ejecucion`).

**¿Por qué mi pool de workers no necesita un `Lock`?**
Porque todos los workers son corrutinas del **mismo hilo**: el event loop solo
puede alternar entre ellas en un `await`. Operaciones como `ocupados += 1` o
`put_nowait` no tienen `await` en el medio, así que son atómicas respecto de las
demás corrutinas. Con threads o procesos sí haría falta un lock (por eso el flag
de cancelación del hash usa un `Event` de `multiprocessing`).

**Si me mandan 10.000 tareas de golpe, ¿qué se rompe primero?**
Lo medí (sección 5.3.1). De 10.000 tareas enviadas de golpe, la API aceptó 5.200 y
rechazó 4.800 con **429** porque la cola llegó a `MAX_COLA=1000`. No se cayó y
todas las aceptadas terminaron, pero lo primero que se degrada es la **latencia de
la API**: el único event loop está ocupado procesando miles de `POST` y
`GET /estadisticas` llegó a tardar 2,2 s (unos milisegundos en reposo). Los workers no son el
cuello de botella de respuesta: siguen consumiendo a ≈ 77 tareas/s. Lo que crece
sin límite es `registros` en RAM, y con él el costo de `GET /tareas`.

**¿Qué diferencia hay entre `gather` y un `for` con `await` adentro?**
Ver sección 6: el `for` es secuencial (suma de tiempos); `gather` es concurrente
(tiempo ≈ el más lento). Medido: 4,14 s vs 0,30 s.

**¿Por qué `time.sleep()` en una corrutina es un bug y `asyncio.sleep()` no?**
`time.sleep()` bloquea el hilo entero, y como el event loop vive en ese hilo, se
congelan todas las corrutinas y el servidor. `asyncio.sleep()` es un `await`:
registra un temporizador y le devuelve el control al loop, que atiende otras
tareas mientras tanto.

## 8. Limitaciones conocidas y seguridad

1. **Sin base de datos:** las tareas viven en memoria. Se vuelcan a JSON al
   detenerse, pero **no se recuperan** al reiniciar (solo se reporta por log).
2. **Una sola instancia:** varios procesos Uvicorn o réplicas tendrían memorias
   independientes; no es una cola distribuida entre máquinas.
3. **Cancelación CPU cooperativa:** no es una interrupción forzosa. El proceso
   debe revisar el flag; `calcular_hash` lo hace cada 1024 iteraciones.
4. **Llamadas síncronas al `Manager`:** crear y activar el `Event` compartido
   bloquea el loop brevemente (ver sección 7).
5. **SSRF:** la URL de `descargar` la elige el cliente, que podría apuntar a
   destinos internos. Antes de publicarlo habría que validar destinos, bloquear
   IP privadas y agregar autenticación.
6. **Histórico ilimitado:** `MAX_COLA` protege la cola, no los registros ya
   terminados; falta una política de caducidad.
7. **Sin paginación:** `GET /tareas` devuelve todo.
8. **FIFO sin prioridades ni reintentos:** una URL que falla queda en su
   resultado, sin reintentar.
9. **Endpoint de laboratorio:** `/experimentos/bloqueo` se habilita por defecto
   en el Compose para poder medir; solo está expuesto en `127.0.0.1`. No debe
   habilitarse en un servidor público.
10. **Mediciones con WSL2:** los tiempos absolutos incluyen la sobrecarga de la
    virtualización y de que cliente y servidor compartan máquina (4 núcleos).
11. **El backpressure no protege al loop:** `MAX_COLA` limita la cola, pero responder
    miles de solicitudes (incluso con 429) satura el event loop y sube la latencia
    (sección 5.3.1). Habría que agregar *rate limiting* por cliente.

## 9. Qué aprendí

El aspecto más importante de este trabajo es entender que concurrencia no
significa necesariamente ejecución paralela de instrucciones de CPU. Cuando un
worker realiza una descarga o una espera, puede ceder el event loop y permitir
que otros trabajos avancen. Por eso una cola asíncrona y varios workers pueden
resolver muchas operaciones I/O sin usar un thread para cada tarea.

El experimento de bloqueo me ayuda a diferenciar I/O-bound de CPU-bound: una
función de hash larga dentro de un `async def` sigue siendo bloqueante aunque el
endpoint esté declarado como asíncrono. Mover ese cálculo a
`ProcessPoolExecutor` permite que los clientes continúen consultando el estado
del sistema, aun cuando el trabajo pesado no haya terminado.

La cancelación resultó más compleja de lo que parece: cancelar una corrutina no
es lo mismo que detener una función en otro proceso. Fue necesario pensar cómo
se propagan las cancelaciones, qué ocurre si hay timeout y cómo liberar recursos
al apagar el servidor. Medir la cola con distintas cantidades de trabajos me
permitió observar un límite que depende de la cantidad de workers y no solo
del event loop.

## 10. Pruebas

```bash
python -m pytest -q
```

Son **9 tests** (`pytest` + `pytest-asyncio`), que cubren: ejecución y
estadísticas, cancelación de tarea en ejecución, cancelación de tarea pendiente,
timeout y errores HTTP (404/422), resultado real de SHA-256, cancelación real de
un hash en otro proceso, límite de la cola, descargas concurrentes contra un
servidor HTTP local y cancelación de descargas en curso. Además, el fixture
comprueba en cada test que el apagado deje un `estado_*.json` válido.
Resultado: **9 passed**.

**Bonus:** tests con `pytest-asyncio`, con foco en cancelación. No se usaron
Celery, RQ ni Dramatiq, y no se usa `requests`.