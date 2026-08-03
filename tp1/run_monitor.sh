#!/usr/bin/env bash

set -e

cleanup() {
    docker compose down >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

# Construye e inicia el servicio
docker compose up --build -d

# Limpiamos la pantalla local antes de conectar curses.
clear

# Una vez conectado, Docker actualiza el tamaño de la PTY.
# Mandamos además SIGWINCH para forzar a curses a reconstruir
# completamente la pantalla.
(
    sleep 1
    docker kill --signal=WINCH tp1-monitor >/dev/null 2>&1 || true
) &

# Conectamos stdin/stdout directamente con la TTY del contenedor.
docker compose attach tp1