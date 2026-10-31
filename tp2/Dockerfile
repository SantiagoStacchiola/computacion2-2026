FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY benchmarks ./benchmarks
RUN mkdir -p /app/volcados
EXPOSE 8000
# Un único proceso uvicorn; el pool de procesos CPU se gestiona internamente.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
