TP1 — Monitor de Procesos y Threads

Computación II — Universidad de Mendoza — 2026Python 3.11+ · Linux · Docker

1. Descripción general

El proyecto implementa un monitor de procesos y threads para Linux, similar en concepto a htop, pero orientado a observar la información interna que el kernel expone en /proc.

La información se obtiene directamente desde archivos como /proc/<pid>/stat, /proc/<pid>/status, /proc/<pid>/fd, /proc/<pid>/task y /proc/<pid>/maps. No se utiliza psutil, ps, top ni herramientas equivalentes.

La aplicación está dividida en procesos independientes: un recolector central obtiene una muestra de /proc, siete analizadores procesan distintas dimensiones de esa muestra, un agregador actualiza el snapshot global compartido y una TUI desarrollada con curses muestra los resultados.

2. Arquitectura

                         /proc
                           │
                           ▼
                    ┌────────────┐
                    │ Recolector │
                    └─────┬──────┘
                          │
        ┌─────────────────┼──────────────────────────┐
        │                 │                          │
        ▼                 ▼                          ▼
   Queue Resumen     Queue Memoria              Queue Sistema
        │                 │                          │
        ▼                 ▼                          ▼
    Analizador         Analizador                  Analizador
      Resumen           Memoria                     Sistema
        │                 │                          │
        └─────────────────┴──────────┬───────────────┘
                                    │
                                    ▼
                           Queue de resultados
                                    │
                                    ▼
                              ┌───────────┐
                              │ Agregador │
                              └─────┬─────┘
                                    │
                                    ▼
                              Manager.dict
                              Snapshot global
                                    │
                                    ▼
                                Display TUI

Existen siete analizadores independientes:

Resumen

Memoria

File descriptors

Threads

Señales

Scheduling

Sistema

Cada analizador tiene su propio intervalo de actualización.

3. IPC y decisiones de diseño

Queue

El recolector distribuye muestras a los analizadores mediante multiprocessing.Queue. Cada cola tiene tamaño 1 para conservar solamente la muestra más reciente y evitar acumular información obsoleta.

Los analizadores envían sus resultados a una cola común consumida por el agregador.

Manager.dict

El snapshot global utiliza multiprocessing.Manager().dict() porque contiene estructuras de tamaño variable: listas de procesos, FDs, threads y diccionarios con distintos tipos de información.

Un Value o un Array no resulta adecuado para representar cómodamente estas estructuras dinámicas.

Value

Los intervalos de las siete vistas utilizan multiprocessing.Value. La TUI modifica el valor de la vista activa con + y -, mientras que cada analizador lo consulta usando el lock asociado.

Agregador

Los analizadores no escriben directamente los resultados de las vistas. El agregador actúa como único escritor y actualiza data, ts y version en el snapshot global.

Esta decisión simplifica la sincronización y reduce posibles race conditions.

Manejo de señales

Para las señales del monitor se utiliza signal.set_wakeup_fd junto con un self-pipe. El handler es mínimo y el trabajo real se procesa fuera del handler.

4. Vistas

Tecla

Vista

Intervalo

1 / r

Resumen

2 s

2 / m

Memoria

3 s

3 / f

File descriptors

5 s

4 / t

Threads

2 s

5 / s

Señales

10 s

6 / p

Scheduling

10 s

7 / g

Sistema

2 s

La TUI mantiene una lista resumida de procesos en la parte superior y muestra abajo el detalle de la vista activa para el proceso seleccionado.

Datos principales

Resumen: PID, PPID, UID/GID, usuario, estado, comando, CPU %, RSS y threads.

Memoria: VmSize, VmRSS, VmData, VmStk, VmExe, VmLib, VmHWM, VmSwap, page faults y segmentos de memoria.

FDs: descriptor, destino y tipo inferido (archivo, tty, socket, pipe, etc.).

Threads: TID, nombre, estado, CPU %, utime, stime y context switches.

Señales: SigBlk, SigIgn, SigCgt, SigPnd y ShdPnd decodificadas a nombres legibles.

Scheduling: nice, priority, policy, RT priority, affinity, context switches, utime, stime, SID y PGID.

Sistema: CPU global, load average, memoria, swap, procesos por estado, threads, zombies, uptime, boot time y top 3 por CPU y memoria.

5. Controles

Tecla

Acción

1-7 o r/m/f/t/s/p/g

Cambiar de vista

↑ / ↓

Navegar por procesos

Enter

Fijar/liberar PID

/

Filtrar por comando

u

Filtrar por usuario

c

Ordenar por CPU / RSS / PID

+ / -

Cambiar intervalo de la vista

h / ?

Ayuda

q

Salir

El PID fijado permanece seleccionado aunque cambie el orden de la lista.

6. Señales del monitor

Señal

Acción

SIGINT

Shutdown limpio

SIGTERM

Shutdown limpio

SIGHUP

Recarga config.json

SIGUSR1

Guarda dump_<timestamp>.json

SIGUSR2

Activa/desactiva modo verbose

SIGWINCH

Fuerza el redibujado

Ejemplos:

docker kill --signal=HUP tp1-monitor
docker kill --signal=USR1 tp1-monitor
docker kill --signal=USR2 tp1-monitor
docker kill --signal=TERM tp1-monitor

7. Race conditions y casos especiales

Un proceso puede desaparecer entre el listado de /proc y la lectura de sus archivos. Por ese motivo las funciones de lectura manejan errores de archivo, permisos y parseo y simplemente omiten ese PID.

Las colas de entrada tienen tamaño 1 para evitar backlog. Los intervalos se acceden mediante el lock de Value y los resultados de los analizadores son publicados por un único agregador.

La TUI utiliza versiones de las vistas y una caché local para redibujar solamente cuando llegan datos nuevos o cuando el usuario realiza una acción.

8. Conceptos de la materia aplicados

Procesos y /proc: lectura de la información que Linux expone para cada proceso.

fork / procesos hijos / zombies: uso de multiprocessing.Process, cierre con join() y detección del estado Z.

Pipes y señales: patrón self-pipe con signal.set_wakeup_fd.

Memoria compartida: Manager.dict y Value.

Multiprocessing: recolector, siete analizadores y agregador ejecutados en procesos independientes.

Threads / LWPs: lectura de /proc/<pid>/task.

Sincronización: colas, locks de Value, agregador único y versionado del snapshot.

9. Ejecución

Docker

Construcción e inicio del servicio:

docker compose up --build

El docker-compose.yml incluye tty: true y stdin_open: true.

En versiones actuales de Docker Compose, compose up puede no reenviar correctamente el teclado a una aplicación curses. Para abrir directamente la TUI interactiva se incluye:

chmod +x run_monitor.sh
./run_monitor.sh

El script construye el mismo servicio, lo inicia y realiza el attach a su TTY.

Ejecución directa en Linux

python3 src/main.py

10. Tests

Los tests utilizan únicamente unittest de la biblioteca estándar.

python3 -m unittest discover -s tests -v

Se prueban helpers de /proc, analizadores, señales decodificadas, CPU de threads, memoria, FDs, scheduling, sistema y actualización del snapshot.

11. Limitaciones conocidas

Dentro de Docker se observan los procesos visibles desde el namespace PID del contenedor.

Algunos procesos pueden desaparecer o volverse inaccesibles mientras se recorren sus archivos en /proc.

El cálculo de CPU se basa en diferencias de jiffies y puede diferir levemente de otras herramientas.

Si un analizador es terminado externamente, actualmente no se reinicia automáticamente.

Según la versión de Docker Compose puede ser necesario utilizar ./run_monitor.sh para la interacción completa con curses.

12. Cómo verificar antes de entregar

python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests

También se puede contrastar manualmente la información con comandos como:

ps -eLf
cat /proc/$$/status
cat /proc/$$/stat
ls -l /proc/$$/fd
cat /proc/loadavg
cat /proc/meminfo | head

Estos comandos son únicamente de verificación; el programa no los ejecuta.

13. Lo que aprendí

El trabajo permitió relacionar los conceptos de procesos, threads, scheduling, señales e IPC con información real expuesta por el kernel en /proc.

También permitió comprobar las diferencias entre comunicación por mensajes y memoria compartida, y la importancia de sincronizar accesos, manejar procesos que desaparecen durante una lectura y mantener los handlers de señales lo más simples posible.

Alumno: [Santiago Stacchiola]Legajo: [64270]