"""Cola, pool de workers, cancelación, timeouts y apagado ordenado."""
from __future__ import annotations

import asyncio
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import json
import logging
import multiprocessing
import os
from pathlib import Path
from typing import Any

from app.models import CrearTarea, Estado, RegistroTarea, ahora
from app.tasks import calcular_hash, descargar, esperar

logger = logging.getLogger(__name__)


class ColaLlenaError(Exception):
    """La cola alcanzó su límite configurado."""


class ManagerTareas:
    def __init__(
        self,
        cantidad_workers: int = 4,
        procesos_cpu: int = 2,
        max_cola: int = 1000,
        carpeta_volcados: str = "volcados",
        gracia_apagado: float = 10.0,
    ) -> None:
        if min(cantidad_workers, procesos_cpu, max_cola) < 1:
            raise ValueError("Workers, procesos y tamaño de cola deben ser >= 1")
        self.cantidad_workers = cantidad_workers
        self.procesos_cpu = procesos_cpu
        self.cola: asyncio.Queue[str] = asyncio.Queue(maxsize=max_cola)
        self.registros: dict[str, RegistroTarea] = {}
        self.workers: list[asyncio.Task[None]] = []
        self.en_ejecucion: dict[str, asyncio.Task[Any]] = {}
        self.senales_cpu: dict[str, Any] = {}
        self.ocupados = 0
        self.acepta_tareas = False
        self.executor: ProcessPoolExecutor | None = None
        self.mp_manager: Any = None
        self.carpeta_volcados = Path(carpeta_volcados)
        self.gracia_apagado = gracia_apagado

    async def iniciar(self) -> None:
        self.carpeta_volcados.mkdir(parents=True, exist_ok=True)
        anteriores = sorted(self.carpeta_volcados.glob("estado_*.json"))
        if anteriores:
            logger.info("Volcado de una ejecución anterior: %s", anteriores[-1])
        else:
            logger.info("No hay volcados anteriores")
        # spawn funciona igual en Linux, Windows y macOS.
        contexto = multiprocessing.get_context("spawn")
        self.mp_manager = contexto.Manager()
        self.executor = ProcessPoolExecutor(
            max_workers=self.procesos_cpu, mp_context=contexto
        )
        self.acepta_tareas = True
        for i in range(self.cantidad_workers):
            self.workers.append(asyncio.create_task(self._worker(i + 1)))
        logger.info("Iniciados %d workers y %d procesos CPU", self.cantidad_workers,
                    self.procesos_cpu)

    def encolar(self, solicitud: CrearTarea) -> RegistroTarea:
        if not self.acepta_tareas:
            raise RuntimeError("El servicio se está apagando")
        if self.cola.full():
            raise ColaLlenaError("La cola está llena; reintentá más tarde")
        registro = RegistroTarea(**solicitud.model_dump())
        self.registros[registro.id] = registro
        # No existe ningún await entre el registro y el put_nowait: no hay carrera
        # entre corrutinas en un solo event loop.
        self.cola.put_nowait(registro.id)
        return registro

    def cancelar(self, id_tarea: str) -> RegistroTarea | None:
        registro = self.registros.get(id_tarea)
        if registro is None:
            return None
        if registro.estado in {Estado.COMPLETADA, Estado.FALLIDA, Estado.CANCELADA}:
            return registro
        registro.cancelacion_solicitada = True
        registro.estado = Estado.CANCELADA
        registro.finalizado_en = ahora()
        registro.error = "Cancelada por solicitud del cliente"
        senal = self.senales_cpu.get(id_tarea)
        if senal is not None:
            # La tarea de proceso verifica el flag cada 1024 hashes.
            senal.set()
        activa = self.en_ejecucion.get(id_tarea)
        if activa is not None:
            activa.cancel()
        # Si sigue en la cola, un worker la descarta al retirarla.
        return registro

    async def _resolver(self, registro: RegistroTarea) -> Any:
        params = registro.parametros
        if registro.tipo == "esperar":
            return await esperar(params["segundos"])
        if registro.tipo == "descargar":
            return await descargar(params["urls"], params["modo"])
        if registro.tipo == "hashear":
            if self.executor is None or self.mp_manager is None:
                raise RuntimeError("El executor no está inicializado")
            senal = self.mp_manager.Event()
            self.senales_cpu[registro.id] = senal
            loop = asyncio.get_running_loop()
            futuro = loop.run_in_executor(
                self.executor, calcular_hash, params["texto"],
                params["iteraciones"], senal
            )
            try:
                # shield impide que cancelar el await destruya el Future interno:
                # el cálculo del proceso recibe el flag de cancelación.
                return await asyncio.shield(futuro)
            except asyncio.CancelledError:
                senal.set()
                # El Future subyacente sigue hasta que el proceso observa el
                # flag; recuperar su eventual excepción evita el warning
                # "Future exception was never retrieved".
                futuro.add_done_callback(
                    lambda f: f.exception() if not f.cancelled() else None
                )
                raise
            finally:
                self.senales_cpu.pop(registro.id, None)
        raise ValueError(f"Tipo de tarea no soportado: {registro.tipo}")

    async def _worker(self, numero: int) -> None:
        while True:
            id_tarea = await self.cola.get()
            try:
                registro = self.registros[id_tarea]
                if registro.estado != Estado.PENDIENTE:
                    continue
                registro.estado = Estado.EJECUTANDO
                registro.iniciado_en = ahora()
                registro.worker_id = numero
                self.ocupados += 1
                ejecucion = asyncio.create_task(self._resolver(registro))
                self.en_ejecucion[id_tarea] = ejecucion
                try:
                    registro.resultado = await asyncio.wait_for(
                        ejecucion, timeout=registro.timeout
                    )
                except asyncio.TimeoutError:
                    if registro.estado != Estado.CANCELADA:
                        registro.estado = Estado.FALLIDA
                        registro.error = f"Timeout de {registro.timeout:g} segundos superado"
                except asyncio.CancelledError:
                    if registro.estado != Estado.CANCELADA:
                        registro.estado = Estado.CANCELADA
                        registro.error = "Cancelada por apagado del servicio"
                    if asyncio.current_task().cancelling():
                        raise
                except Exception as exc:
                    logger.exception("Falló tarea %s", id_tarea)
                    if registro.estado != Estado.CANCELADA:
                        registro.estado = Estado.FALLIDA
                        registro.error = f"{type(exc).__name__}: {exc}"
                else:
                    if registro.estado != Estado.CANCELADA:
                        registro.estado = Estado.COMPLETADA
                finally:
                    self.en_ejecucion.pop(id_tarea, None)
                    if registro.finalizado_en is None:
                        registro.finalizado_en = ahora()
                    self.ocupados -= 1
            finally:
                self.cola.task_done()

    def estadisticas(self) -> dict[str, Any]:
        conteos = Counter(r.estado.value for r in self.registros.values())
        duraciones = [r.duracion_segundos for r in self.registros.values()
                      if r.duracion_segundos is not None]
        esperas = [(r.iniciado_en - r.creado_en).total_seconds()
                   for r in self.registros.values() if r.iniciado_en is not None]
        return {
            "total_tareas": len(self.registros),
            "por_estado": {e.value: conteos[e.value] for e in Estado},
            "tiempo_promedio_ejecucion_segundos": (
                round(sum(duraciones) / len(duraciones), 4) if duraciones else None
            ),
            "tiempo_promedio_espera_segundos": (
                round(sum(esperas) / len(esperas), 4) if esperas else None
            ),
            "workers_totales": self.cantidad_workers,
            "workers_ocupados": self.ocupados,
            "workers_libres": self.cantidad_workers - self.ocupados,
            "tareas_pendientes": conteos[Estado.PENDIENTE.value],
            "cola_elementos_sin_retirar": self.cola.qsize(),
            "aceptando_tareas": self.acepta_tareas,
        }

    async def detener(self) -> Path:
        self.acepta_tareas = False
        logger.info("Apagado ordenado: esperando hasta %.1fs", self.gracia_apagado)
        try:
            await asyncio.wait_for(self.cola.join(), timeout=self.gracia_apagado)
        except asyncio.TimeoutError:
            logger.warning("Terminó el tiempo de gracia; cancelando tareas restantes")
        for id_tarea, registro in self.registros.items():
            if registro.estado in {Estado.PENDIENTE, Estado.EJECUTANDO}:
                self.cancelar(id_tarea)
                registro.error = "Cancelada por apagado del servicio"
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        # Espera al fin de los procesos; los hashes observan el flag de cancelación.
        if self.executor is not None:
            await asyncio.to_thread(self.executor.shutdown, wait=True,
                                    cancel_futures=True)
        if self.mp_manager is not None:
            await asyncio.to_thread(self.mp_manager.shutdown)
        self.carpeta_volcados.mkdir(parents=True, exist_ok=True)
        marca = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        archivo = self.carpeta_volcados / f"estado_{marca}.json"
        datos = {
            "generado_en": ahora().isoformat(),
            "tareas": [r.model_dump(mode="json") for r in self.registros.values()],
        }
        contenido = json.dumps(datos, indent=2, ensure_ascii=False)
        await asyncio.to_thread(archivo.write_text, contenido, encoding="utf-8")
        logger.info("Estado guardado: %s", archivo)
        return archivo


def manager_desde_entorno() -> ManagerTareas:
    return ManagerTareas(
        cantidad_workers=int(os.getenv("CANTIDAD_WORKERS", "4")),
        procesos_cpu=int(os.getenv("PROCESOS_CPU", "2")),
        max_cola=int(os.getenv("MAX_COLA", "1000")),
        carpeta_volcados=os.getenv("CARPETA_VOLCADOS", "volcados"),
        gracia_apagado=float(os.getenv("GRACIA_APAGADO", "10")),
    )
