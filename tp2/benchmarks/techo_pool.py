"""Medición 3 extendida: techo del pool con cargas grandes.

Para cada nivel envía N tareas de golpe y registra:
  - cuántas aceptó la API (202) y cuántas rechazó (429, cola llena)
  - cuánto tardó en terminar todo y el rendimiento (tareas/seg)
  - la latencia de GET /estadisticas y GET /tareas bajo carga

Uso (con el servidor levantado):
    python benchmarks/techo_pool.py
    python benchmarks/techo_pool.py --niveles 100 500 1000 2000 5000 10000
    python benchmarks/techo_pool.py --tipo hashear --iteraciones 200000 --niveles 10 50 100 500

Conviene reiniciar el servidor entre corridas (docker compose restart): los
registros viejos se acumulan en RAM y afectan la latencia de los GET.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import platform
import time

import httpx


def armar_cuerpo(args) -> dict:
    if args.tipo == "esperar":
        parametros = {"segundos": args.duracion}
    else:
        parametros = {"texto": "benchmark", "iteraciones": args.iteraciones}
    return {"tipo": args.tipo, "parametros": parametros, "timeout": 300}


async def latencia(cliente: httpx.AsyncClient, ruta: str) -> float:
    inicio = time.perf_counter()
    r = await cliente.get(ruta)
    r.raise_for_status()
    return round(time.perf_counter() - inicio, 4)


async def enviar_todas(cliente, cuerpo, n, concurrencia):
    """Envía n POST con a lo sumo `concurrencia` en vuelo. Cuenta 202 y 429."""
    sem = asyncio.Semaphore(concurrencia)
    codigos: list[int] = []

    async def una():
        async with sem:
            r = await cliente.post("/tareas", json=cuerpo)
            codigos.append(r.status_code)

    await asyncio.gather(*(una() for _ in range(n)))
    return codigos


async def esperar_vaciado(cliente, limite):
    """Espera hasta que no queden tareas pendientes ni ejecutando."""
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < limite:
        est = (await cliente.get("/estadisticas")).json()["por_estado"]
        if est["pendiente"] + est["ejecutando"] == 0:
            return True
        await asyncio.sleep(0.2)
    return False


async def medir_nivel(cliente, cuerpo, n, concurrencia, limite):
    lat_stats_durante: list[float] = []
    detener = asyncio.Event()

    async def sondeo():
        # Mide la latencia de la API mientras hay carga.
        while not detener.is_set():
            lat_stats_durante.append(await latencia(cliente, "/estadisticas"))
            await asyncio.sleep(0.1)

    sonda = asyncio.create_task(sondeo())
    inicio = time.perf_counter()
    codigos = await enviar_todas(cliente, cuerpo, n, concurrencia)
    t_envio = time.perf_counter() - inicio
    terminado = await esperar_vaciado(cliente, limite)
    t_total = time.perf_counter() - inicio
    detener.set()
    await sonda

    aceptadas = codigos.count(202)
    rechazadas = codigos.count(429)
    otros = len(codigos) - aceptadas - rechazadas
    return {
        "enviadas": n,
        "aceptadas_202": aceptadas,
        "rechazadas_429": rechazadas,
        "otros_codigos": otros,
        "tiempo_envio_segundos": round(t_envio, 3),
        "tiempo_total_segundos": round(t_total, 3),
        "terminaron_todas": terminado,
        "tareas_por_segundo": round(aceptadas / t_total, 2) if t_total else None,
        "latencia_estadisticas_durante_carga_max_s": max(lat_stats_durante, default=None),
        "latencia_estadisticas_durante_carga_prom_s": (
            round(sum(lat_stats_durante) / len(lat_stats_durante), 4)
            if lat_stats_durante else None
        ),
        "latencia_get_tareas_despues_s": await latencia(cliente, "/tareas"),
        "latencia_get_estadisticas_despues_s": await latencia(cliente, "/estadisticas"),
    }


async def principal(args):
    cuerpo = armar_cuerpo(args)
    resultados = []
    limites = httpx.Limits(max_connections=args.concurrencia + 10)
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120,
                                 limits=limites) as cliente:
        config = (await cliente.get("/estadisticas")).json()
        print(f"Workers del servidor: {config['workers_totales']}")
        print(f"{'N':>7} {'202':>6} {'429':>6} {'envio s':>8} {'total s':>8} "
              f"{'tareas/s':>9} {'lat stats max':>14} {'GET /tareas':>12}")
        for n in args.niveles:
            r = await medir_nivel(cliente, cuerpo, n, args.concurrencia, args.limite)
            resultados.append(r)
            print(f"{n:>7} {r['aceptadas_202']:>6} {r['rechazadas_429']:>6} "
                  f"{r['tiempo_envio_segundos']:>8} {r['tiempo_total_segundos']:>8} "
                  f"{r['tareas_por_segundo']:>9} "
                  f"{r['latencia_estadisticas_durante_carga_max_s']!s:>14} "
                  f"{r['latencia_get_tareas_despues_s']:>12}")
    salida = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "plataforma_cliente": platform.platform(),
        "python_cliente": platform.python_version(),
        "servidor": args.base_url,
        "tipo_tarea": args.tipo,
        "duracion_tarea_segundos": args.duracion if args.tipo == "esperar" else None,
        "iteraciones": args.iteraciones if args.tipo == "hashear" else None,
        "workers_servidor": config["workers_totales"],
        "niveles": resultados,
    }
    with open(args.salida, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--niveles", type=int, nargs="+",
                   default=[100, 500, 1000, 2000, 5000, 10000])
    p.add_argument("--tipo", choices=["esperar", "hashear"], default="esperar")
    p.add_argument("--duracion", type=float, default=0.05,
                   help="segundos de cada tarea 'esperar'")
    p.add_argument("--iteraciones", type=int, default=200_000,
                   help="iteraciones de cada tarea 'hashear'")
    p.add_argument("--concurrencia", type=int, default=100,
                   help="POST simultáneos desde el cliente")
    p.add_argument("--limite", type=float, default=600,
                   help="segundos máximos de espera por nivel")
    p.add_argument("--salida", default="resultados_techo_pool.json")
    asyncio.run(principal(p.parse_args()))