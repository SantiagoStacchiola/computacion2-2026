def chunked(iterable, size):
    chunk = []

    for elemento in iterable:
        chunk.append(elemento)

        if len(chunk) == size:
            yield chunk
            chunk = []

    if chunk:
        yield chunk


# Pruebas
print(list(chunked(range(10), 3)))
print(list(chunked("abcdefgh", 3)))