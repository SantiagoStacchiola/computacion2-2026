from flask import Flask
import redis
import os

app = Flask(__name__)

redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379)

@app.route("/")
def home():
    try:
        contador = r.get("contador")
        if contador:
            contador = contador.decode()
        else:
            contador = "0"
    except:
        contador = "Error conectando a Redis"

    return f"Contador actual: {contador}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)