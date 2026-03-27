from functools import wraps
from collections import namedtuple

CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "size"])

def memoize(func):
    cache = {}
    hits = 0
    misses = 0

    @wraps(func)
    def wrapper(*args):
        nonlocal hits, misses

        if args in cache:
            hits += 1
            return cache[args]

        misses += 1
        resultado = func(*args)
        cache[args] = resultado
        return resultado

    wrapper.cache = cache

    def cache_info():
        return CacheInfo(hits=hits, misses=misses, size=len(cache))

    def clear_cache():
        nonlocal hits, misses
        cache.clear()
        hits = 0
        misses = 0

    wrapper.cache_info = cache_info
    wrapper.clear_cache = clear_cache

    return wrapper


@memoize
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


print(fibonacci(100))
print(fibonacci.cache)
print(fibonacci.cache_info())

fibonacci.clear_cache()
print(fibonacci.cache)
print(fibonacci.cache_info())