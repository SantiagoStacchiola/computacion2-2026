"""Implementaciones de trabajo: I/O real, I/O simulado y CPU-bound."""
from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

import httpx


# Esta función vive al nivel del módulo: ProcessPoolExecutor puede serializarla.
def calcular_hash(texto: str, iteraciones: int, detener: Any = None) -> dict[str, Any]:
    """Aplica SHA-256 repetidamente; revisa una señal cooperativa de cancelación.

    Se ejecuta en otro PROCESO, no dentro del event loop de FastAPI.
    """
    inicio = time.perf_counter()
    actual = texto.encode("utf-8")
    for i in range(iteraciones):
        if i % 1024 == 0 and detener is not None and detener.is_set():
            raise RuntimeError("Cálculo detenido por cancelación o timeout")
        actual = hashlib.sha256(actual).digest()
    return {
        "sha256": actual.hex(),
        "iteraciones": iteraciones,
        "duracion_calculo_segundos": round(time.perf_counter() - inicio, 4),
    }


async def esperar(segundos: float) -> dict[str, float]:
    # asyncio.sleep cede el control al event loop; time.sleep lo bloquearía.
    await asyncio.sleep(segundos)
    return {"segundos_esperados": segundos}


async def _una_descarga(
    cliente: httpx.AsyncClient, url: str, max_bytes: int = 5_000_000
) -> dict[str, Any]:
    inicio = time.perf_counter()
    try:
        async with cliente.stream("GET", url) as respuesta:
            total = 0
            async for bloque in respuesta.aiter_bytes():
                total += len(bloque)
                if total > max_bytes:
                    raise ValueError(f"Respuesta mayor a {max_bytes} bytes")
            return {
                "url": url,
                "codigo_estado": respuesta.status_code,
                "tamano_bytes": total,
                "tiempo_segundos": round(time.perf_counter() - inicio, 4),
            }
    except (httpx.RequestError, ValueError) as exc:
        # Errores por URL no impiden que las demás descargas se completen.
        return {
            "url": url,
            "codigo_estado": None,
            "tamano_bytes": 0,
            "tiempo_segundos": round(time.perf_counter() - inicio, 4),
            "error": str(exc),
        }


async def descargar(urls: list[str], modo: str = "concurrente") -> dict[str, Any]:
    inicio = time.perf_counter()
    limite = httpx.Limits(max_connections=25, max_keepalive_connections=25)
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(20.0),
        limits=limite,
    ) as cliente:
        if modo == "secuencial":
            resultados = []
            for url in urls:
                resultados.append(await _una_descarga(cliente, url))
        else:
            # gather inicia las corrutinas juntas; si se cancela, cancela hijas.
            resultados = await asyncio.gather(
                *(_una_descarga(cliente, url) for url in urls)
            )
    exitosas = sum(1 for r in resultados if r.get("codigo_estado") is not None
                   and 200 <= r["codigo_estado"] < 400)
    return {
        "modo": modo,
        "cantidad": len(urls),
        "exitosas": exitosas,
        "tiempo_total_segundos": round(time.perf_counter() - inicio, 4),
        "descargas": resultados,
    }
