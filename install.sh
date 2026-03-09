#!/usr/bin/env bash
# ============================================================
# install.sh — Setup inicial do Trending Article Recommender
# ============================================================
set -e

VENV_DIR=".venv"
ENV_FILE=".env"

echo ""
echo "=== Trending Article Recommender — Instalação ==="
echo ""

# Verifica Python 3.9+
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python 3 não encontrado. Instale Python >= 3.9."
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PY_VERSION encontrado"

# Cria virtualenv
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Criando ambiente virtual..."
    python3 -m venv "$VENV_DIR"
    echo "[OK] Ambiente virtual criado em $VENV_DIR"
fi

# Ativa e instala dependências
echo "→ Instalando dependências (pode demorar alguns minutos)..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r requirements.txt -q
echo "[OK] Dependências instaladas"

# Copia .env se não existir
if [ ! -f "$ENV_FILE" ]; then
    cp .env.example "$ENV_FILE"
    echo "[OK] Arquivo .env criado a partir de .env.example"
else
    echo "[OK] Arquivo .env já existe"
fi

echo ""
echo "=== Instalação concluída! ==="
echo ""
echo "Para iniciar o servidor:"
echo "  ./start.sh"
echo ""
echo "Para usar a CLI:"
echo "  $VENV_DIR/bin/python cli.py --help"
echo ""
