"""API FastAPI. Ejecución: uvicorn app.main:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

from contextlib import asynccontextmanager
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, status

from app.manager import ColaLlenaError, manager_desde_entorno
from app.models import CrearTarea, Estado, RegistroTarea
from app.tasks import calcular_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    gestor = manager_desde_entorno()
    app.state.gestor = gestor
    await gestor.iniciar()
    try:
        yield
    finally:
        await gestor.detener()


app = FastAPI(
    title="TP2 — Plataforma de Tareas Distribuidas",
    description="API de tareas concurrentes, cancelación y mediciones — Computación II",
    version="1.0.0",
    lifespan=lifespan,
)


def get_gestor(request: Request):
    return request.app.state.gestor


@app.get("/salud")
async def salud() -> dict[str, str]:
    return {"estado": "ok"}


@app.post("/tareas", response_model=RegistroTarea,
          status_code=status.HTTP_202_ACCEPTED)
async def crear_tarea(solicitud: CrearTarea, request: Request) -> RegistroTarea:
    gestor = get_gestor(request)
    try:
        return gestor.encolar(solicitud)
    except ColaLlenaError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/tareas", response_model=list[RegistroTarea])
async def listar_tareas(request: Request, estado: Estado | None = None):
    registros = get_gestor(request).registros.values()
    return [r for r in registros if estado is None or r.estado == estado]


@app.get("/tareas/{id_tarea}", response_model=RegistroTarea)
async def consultar_tarea(id_tarea: str, request: Request):
    registro = get_gestor(request).registros.get(id_tarea)
    if registro is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return registro


@app.delete("/tareas/{id_tarea}", response_model=RegistroTarea)
async def cancelar_tarea(id_tarea: str, request: Request):
    registro = get_gestor(request).cancelar(id_tarea)
    if registro is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return registro


@app.get("/estadisticas")
async def estadisticas(request: Request) -> dict[str, Any]:
    return get_gestor(request).estadisticas()


# Endpoint local para que los benchmarks de I/O sean reproducibles y no dependan
# de sitios externos. Se habilita solamente con HABILITAR_EXPERIMENTOS=1.
if os.getenv("HABILITAR_EXPERIMENTOS", "0") == "1":
    import asyncio

    @app.get("/experimentos/latencia")
    async def latencia(segundos: float = Query(0.25, ge=0, le=5)):
        await asyncio.sleep(segundos)
        return {"simulacion": "respuesta remota", "segundos": segundos}

    @app.post("/experimentos/bloqueo")
    async def bloqueo(iteraciones: int = Query(4_000_000, ge=1, le=30_000_000)):
        # ¡INTENCIONALMENTE MAL! Solo para medir cómo se congela el event loop.
        # Nunca invocar este código desde un endpoint de producción.
        return calcular_hash("demostracion", iteraciones)


# Sin recarga ni multiples instancias: el estado en memoria es por proceso.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False,
                workers=1)
