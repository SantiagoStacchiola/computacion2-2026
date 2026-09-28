import asyncio


async def tarea(nombre, segundos):
    print(f'{nombre}: empieza')

    await asyncio.sleep(segundos)

    print(f'{nombre}: termina')


async def main():
    await asyncio.gather(
        tarea('A', 0.3),
        tarea('B', 0.1),
        tarea('C', 0.2)
    )


asyncio.run(main())