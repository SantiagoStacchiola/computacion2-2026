"""Pruebas end-to-end de ASGI, incluido lifecycle y casos concurrentes."""
import asyncio
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time

import httpx
import pytest

from app.main import app
from app.models import CrearTarea, Estado
from app.manager import ColaLlenaError, ManagerTareas


@pytest.fixture
async def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("CARPETA_VOLCADOS", str(tmp_path))
    monkeypatch.setenv("CANTIDAD_WORKERS", "2")
    monkeypatch.setenv("PROCESOS_CPU", "1")
    monkeypatch.setenv("GRACIA_APAGADO", "0.2")
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport,
                                    base_url="http://test") as client:
            yield client
    volcados = list(tmp_path.glob("estado_*.json"))
    assert len(volcados) == 1
    datos = json.loads(volcados[0].read_text(encoding="utf-8"))
    assert "tareas" in datos


async def esperar_estado(cliente, id_tarea, esperados, max_espera=5):
    async def check():
        while True:
            r = await cliente.get(f"/tareas/{id_tarea}")
            assert r.status_code == 200
            dato = r.json()
            if dato["estado"] in esperados:
                return dato
            await asyncio.sleep(0.01)

    return await asyncio.wait_for(check(), max_espera)


@pytest.mark.asyncio
async def test_tarea_esperar_y_estadisticas(cliente):
    r = await cliente.post("/tareas", json={
        "tipo": "esperar", "parametros": {"segundos": 0.05}, "timeout": 3
    })
    assert r.status_code == 202
    assert r.json()["estado"] == "pendiente"
    id_tarea = r.json()["id"]
    resultado = await esperar_estado(cliente, id_tarea, {"completada"})
    assert resultado["resultado"]["segundos_esperados"] == 0.05
    lista = (await cliente.get("/tareas", params={"estado": "completada"})).json()
    assert any(t["id"] == id_tarea for t in lista)
    stats = (await cliente.get("/estadisticas")).json()
    assert stats["por_estado"]["completada"] == 1
    assert stats["workers_ocupados"] == 0


@pytest.mark.asyncio
async def test_cancelar_durante_ejecucion(cliente):
    r = await cliente.post("/tareas", json={
        "tipo": "esperar", "parametros": {"segundos": 3}, "timeout": 5
    })
    tid = r.json()["id"]
    await esperar_estado(cliente, tid, {"ejecutando"})
    eliminado = await cliente.delete(f"/tareas/{tid}")
    assert eliminado.status_code == 200
    assert eliminado.json()["estado"] == "cancelada"
    await asyncio.sleep(0.05)
    assert (await cliente.get("/estadisticas")).json()["workers_ocupados"] == 0


@pytest.mark.asyncio
async def test_cancelar_pendiente(cliente):
    tareas = []
    for _ in range(3):
        respuesta = await cliente.post("/tareas", json={
            "tipo": "esperar", "parametros": {"segundos": 2}, "timeout": 5
        })
        tareas.append(respuesta.json()["id"])
    assert (await cliente.delete(f"/tareas/{tareas[2]}")).json()["estado"] == "cancelada"
    for tid in tareas[:2]:
        await cliente.delete(f"/tareas/{tid}")
    await asyncio.sleep(0.05)
    assert (await cliente.get(f"/tareas/{tareas[2]}")).json()["iniciado_en"] is None


@pytest.mark.asyncio
async def test_timeout_y_errores_http(cliente):
    r = await cliente.post("/tareas", json={
        "tipo": "esperar", "parametros": {"segundos": 1}, "timeout": 0.05
    })
    registro = await esperar_estado(cliente, r.json()["id"], {"fallida"})
    assert "Timeout" in registro["error"]
    assert (await cliente.get("/tareas/identificador-inexistente")).status_code == 404
    assert (await cliente.delete("/tareas/identificador-inexistente")).status_code == 404
    invalida = await cliente.post("/tareas", json={
        "tipo": "hashear", "parametros": {"texto": "abc", "iteraciones": -1}
    })
    assert invalida.status_code == 422


@pytest.mark.asyncio
async def test_hashear_en_proceso(cliente):
    r = await cliente.post("/tareas", json={
        "tipo": "hashear",
        "parametros": {"texto": "abc", "iteraciones": 100},
        "timeout": 10,
    })
    assert r.status_code == 202
    final = await esperar_estado(cliente, r.json()["id"],
                                 {"completada", "fallida"}, max_espera=10)
    assert final["estado"] == "completada", final.get("error")
    estado = b"abc"
    for _ in range(100):
        estado = hashlib.sha256(estado).digest()
    assert final["resultado"]["sha256"] == estado.hex()


@pytest.mark.asyncio
async def test_cancelar_hash_real(cliente):
    r = await cliente.post("/tareas", json={
        "tipo": "hashear",
        "parametros": {"texto": "abc", "iteraciones": 20_000_000},
        "timeout": 60,
    })
    tid = r.json()["id"]
    await esperar_estado(cliente, tid, {"ejecutando"})
    assert (await cliente.delete(f"/tareas/{tid}")).json()["estado"] == "cancelada"
    await asyncio.sleep(0.2)
    assert (await cliente.get("/estadisticas")).json()["workers_ocupados"] == 0


def test_cola_limitada():
    gestor = ManagerTareas(cantidad_workers=1, procesos_cpu=1, max_cola=1)
    gestor.acepta_tareas = True
    solicitud = CrearTarea(tipo="esperar", parametros={"segundos": 1})
    gestor.encolar(solicitud)
    with pytest.raises(ColaLlenaError):
        gestor.encolar(solicitud)


@pytest.fixture
def servidor_http_local():
    """Servidor deliberadamente lento para comprobar descargas HTTP reales."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(0.2)
            datos = b"respuesta de prueba"
            self.send_response(200)
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            try:
                self.wfile.write(datos)
            except (ConnectionAbortedError, BrokenPipeError):
                # El cliente pudo cancelar la descarga: es el caso que probamos.
                pass

        def log_message(self, *args):
            pass

    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}/archivo"
    servidor.shutdown()
    servidor.server_close()
    hilo.join(timeout=1)


@pytest.mark.asyncio
async def test_descargar_concurrente_real(cliente, servidor_http_local):
    inicio = time.perf_counter()
    res = await cliente.post("/tareas", json={
        "tipo": "descargar",
        "parametros": {"urls": [servidor_http_local] * 5},
        "timeout": 5,
    })
    final = await esperar_estado(cliente, res.json()["id"], {"completada", "fallida"})
    total = time.perf_counter() - inicio
    assert final["estado"] == "completada", final["error"]
    assert final["resultado"]["exitosas"] == 5
    assert all(r["codigo_estado"] == 200 for r in final["resultado"]["descargas"])
    assert all(r["tamano_bytes"] == 19 for r in final["resultado"]["descargas"])
    assert total < 0.95, f"Se esperaba concurrencia real, tardó {total:.3f}s"


@pytest.mark.asyncio
async def test_cancelar_descarga_en_ejecucion(cliente, servidor_http_local):
    res = await cliente.post("/tareas", json={
        "tipo": "descargar",
        "parametros": {"urls": [servidor_http_local] * 10},
        "timeout": 5,
    })
    tid = res.json()["id"]
    await esperar_estado(cliente, tid, {"ejecutando"})
    cancelada = await cliente.delete(f"/tareas/{tid}")
    assert cancelada.json()["estado"] == "cancelada"
    await asyncio.sleep(0.05)
    assert (await cliente.get("/estadisticas")).json()["workers_ocupados"] == 0
