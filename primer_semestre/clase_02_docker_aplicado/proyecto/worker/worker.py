import redis
import time
import os

redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379)

print("Worker iniciado...")

while True:
    r.incr("contador")
    print("Incrementando contador...")
    time.sleep(1)