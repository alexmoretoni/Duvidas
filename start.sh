#!/usr/bin/env bash
# ============================================================
# start.sh — Inicia o servidor da API
# Uso: ./start.sh [--port 8000] [--reload]
# ============================================================
set -e

VENV_DIR=".venv"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

# Verifica se o venv existe
if [ ! -d "$VENV_DIR" ]; then
    echo "Ambiente virtual não encontrado. Executando install.sh..."
    bash install.sh
fi

# Verifica .env
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

echo ""
echo "=== Trending Article Recommender ==="
echo "→ Iniciando servidor em http://$HOST:$PORT"
echo "→ Documentação: http://localhost:$PORT/docs"
echo ""

"$VENV_DIR/bin/python" cli.py serve --host "$HOST" --port "$PORT" "$@"
