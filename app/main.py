"""
Trending Article Recommender — API FastAPI

Inicia com:
    uvicorn app.main:app --reload
ou:
    python cli.py serve
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routers import articles, recommend, trends

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando banco de dados...")
    await init_db()
    logger.info("API pronta. Docs em /docs")
    yield
    logger.info("Encerrando API.")


app = FastAPI(
    title="Trending Article Recommender",
    description=(
        "Sistema que analisa trends e tópicos em alta e recomenda artigos "
        "através de palavras-chave, URLs, categorias, cidades, países e idiomas.\n\n"
        "**Fontes de dados:**\n"
        "- Google Trends (via pytrends)\n"
        "- Google News RSS (sem API key)\n"
        "- 30+ feeds RSS públicos (Brasil, Portugal, EUA, UK, França, Alemanha, Espanha, Argentina)\n\n"
        "**Idioma padrão:** Português (Brasil)"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra routers
app.include_router(trends.router)
app.include_router(articles.router)
app.include_router(recommend.router)


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({
        "name": "Trending Article Recommender",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "trends": "/trends",
            "trending_keywords": "/trends/keywords",
            "search": "/articles/search",
            "recommend": "/recommend",
            "sources": "/articles/sources/list",
            "health": "/health",
        },
    })


@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "ok", "default_country": settings.default_country, "default_language": settings.default_language}
