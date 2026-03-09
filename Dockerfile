FROM python:3.11-slim

LABEL maintainer="Trending Article Recommender"
LABEL description="Sistema de análise de trends e recomendação de artigos"

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python primeiro (aproveita cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY . .

# Configura o .env padrão (pode ser sobrescrito via volume ou env_file)
RUN test -f .env || cp .env.example .env

# Expõe a porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Usuário não-root por segurança
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Comando de inicialização
CMD ["python", "cli.py", "serve", "--host", "0.0.0.0", "--port", "8000"]
