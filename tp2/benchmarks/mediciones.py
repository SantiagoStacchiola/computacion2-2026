"""Tres mediciones pedidas por el TP.

Uso (desde el host):
    python benchmarks/mediciones.py --base-url http://127.0.0.1:8000
Se requiere HABILITAR_EXPERIMENTOS=1 en docker-compose (solo laboratorio).
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import time

import httpx


ESTADOS_FINALES = {"completada", "fallida", "cancelada"}


async def esperar_final(cliente: httpx.AsyncClient, id_tarea: str, limite: float = 180):
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < limite:
        respuesta = await cliente.get(f"/tareas/{id_tarea}")
        respuesta.raise_for_status()
        tarea = respuesta.json()
        if tarea["estado"] in ESTADOS_FINALES:
            if tarea["estado"] != "completada":
                raise RuntimeError(f"Tarea no completada: {tarea['error']}")
            return tarea
        await asyncio.sleep(0.025)
    raise TimeoutError(f"La tarea {id_tarea} no terminó en {limite}s")


async def publicar(cliente, tipo, parametros, timeout=150):
    respuesta = await cliente.post("/tareas", json={
        "tipo": tipo, "parametros": parametros, "timeout": timeout
    })
    respuesta.raise_for_status()
    return respuesta.json()["id"]


async def medir_descargas(cliente, base_url: str, demora: float, repeticiones: int):
    # Mismas 20 URL, mismo endpoint local asíncrono, 2 modalidades.
    urls = [f"{base_url}/experimentos/latencia?segundos={demora}"] * 20
    registro = {"secuencial": [], "concurrente": []}
    for _ in range(repeticiones):
        for modo in ("secuencial", "concurrente"):
            inicio = time.perf_counter()
            ident = await publicar(cliente, "descargar", {"urls": urls, "modo": modo})
            resultado = await esperar_final(cliente, ident)
            duracion = time.perf_counter() - inicio
            if resultado["resultado"]["exitosas"] != 20:
                raise RuntimeError("Falló una descarga durante la medición")
            registro[modo].append(round(duracion, 4))
    secuencial = statistics.mean(registro["secuencial"])
    concurrente = statistics.mean(registro["concurrente"])
    return {
        "numero_urls": 20,
        "demora_endpoint_segundos": demora,
        "repeticiones": repeticiones,
        "tiempos_segundos": registro,
        "promedio_secuencial_segundos": round(secuencial, 4),
        "promedio_concurrente_segundos": round(concurrente, 4),
        "speedup": round(secuencial / concurrente, 2),
    }


async def medir_bloqueo(cliente, iteraciones: int):
    # Antes: CPU ejecutado dentro de async def SIN await (mal, bloquea event loop).
    async def cronometrar_get():
        inicio = time.perf_counter()
        respuesta = await cliente.get("/tareas")
        respuesta.raise_for_status()
        return round(time.perf_counter() - inicio, 4)

    inicio = time.perf_counter()
    tarea_bloqueante = asyncio.create_task(
        cliente.post(f"/experimentos/bloqueo?iteraciones={iteraciones}", timeout=180)
    )
    await asyncio.sleep(0.1)
    get_bloqueado = await cronometrar_get()
    respuesta = await tarea_bloqueante
    respuesta.raise_for_status()
    tiempo_total = round(time.perf_counter() - inicio, 4)

    # Después: misma cantidad de hashes dentro de ProcessPoolExecutor.
    ident = await publicar(cliente, "hashear", {
        "texto": "demostracion", "iteraciones": iteraciones
    }, timeout=180)
    await asyncio.sleep(0.1)
    get_executor = await cronometrar_get()
    await esperar_final(cliente, ident)
    return {
        "iteraciones": iteraciones,
        "get_mientras_bloquea_segundos": get_bloqueado,
        "get_con_executor_segundos": get_executor,
        "factor_latencia": round(get_bloqueado / max(get_executor, .0001), 2),
        "tiempo_total_bloqueo_segundos": tiempo_total,
    }


async def medir_pool(cliente, demora: float, cantidades: list[int]):
    resultados = []
    for cantidad in cantidades:
        inicio = time.perf_counter()
        ids = await asyncio.gather(*[
            publicar(cliente, "esperar", {"segundos": demora})
            for _ in range(cantidad)
        ])
        await asyncio.gather(*[esperar_final(cliente, ident) for ident in ids])
        total = round(time.perf_counter() - inicio, 4)
        resultados.append({"cantidad_tareas": cantidad,
                           "tiempo_total_segundos": total})
    return {"duracion_individual_segundos": demora, "mediciones": resultados}


async def ejecutar(args):
    base = args.base_url.rstrip("/")
    async with httpx.AsyncClient(base_url=base, timeout=180,
                                 limits=httpx.Limits(max_connections=100)) as cliente:
        salud = await cliente.get("/salud")
        salud.raise_for_status()
        prueba = await cliente.get("/experimentos/latencia?segundos=0")
        if prueba.status_code != 200:
            raise RuntimeError("Habilitá HABILITAR_EXPERIMENTOS=1 en el servidor")
        print("1/3 Midiendo 20 descargas secuenciales y concurrentes...")
        io = await medir_descargas(cliente, base, args.demora, args.repeticiones)
        print("  Speedup:", io["speedup"], "x")
        print("2/3 Midiendo event loop bloqueado y executor...")
        cpu = await medir_bloqueo(cliente, args.iteraciones)
        print("  Latencias GET (sin/con executor):",
              cpu["get_mientras_bloquea_segundos"], "/",
              cpu["get_con_executor_segundos"], "s")
        print("3/3 Midiendo techo del pool...")
        pool = await medir_pool(cliente, args.demora_pool, [1, 2, 4, 8, 16, 32])
        print("  Cantidad de workers:", (await cliente.get("/estadisticas")).json()["workers_totales"])
    datos = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "plataforma_cliente": platform.platform(),
        "python_cliente": platform.python_version(),
        "servidor": base,
        "concurrencia_io": io,
        "bloqueo_event_loop": cpu,
        "techo_pool": pool,
    }
    salida = Path(args.salida)
    salida.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Datos reales guardados en {salida}")
    print("Pegá los valores de este JSON en la sección 'Mediciones' del README.")


def main():
    parser = argparse.ArgumentParser(description="Benchmarks del TP2")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--demora", type=float, default=0.2)
    parser.add_argument("--demora-pool", type=float, default=0.4)
    parser.add_argument("--repeticiones", type=int, default=2)
    parser.add_argument("--iteraciones", type=int, default=4_000_000)
    parser.add_argument("--salida", default="resultados_mediciones.json")
    args = parser.parse_args()
    asyncio.run(ejecutar(args))


if __name__ == "__main__":
    main()
