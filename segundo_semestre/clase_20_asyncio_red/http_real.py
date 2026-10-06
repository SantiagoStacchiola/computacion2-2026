import asyncio
import httpx


async def bajar(cliente, url):
    respuesta = await cliente.get(url)
    return url, respuesta.status_code, len(respuesta.content)


async def main():
    urls = [
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
        "https://example.com",
    ]

    async with httpx.AsyncClient(timeout=10) as cliente:
        resultados = await asyncio.gather(
            *(bajar(cliente, url) for url in urls)
        )

        for url, codigo, tam in resultados:
            print(f"{codigo} {tam} bytes {url}")


asyncio.run(main())