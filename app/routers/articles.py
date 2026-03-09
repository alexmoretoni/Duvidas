from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app import crud
from app.config import settings
from app.recommender.engine import search_articles
from app.schemas import Article, ArticleSearchRequest, RSSSource
from app.trends.rss_fetcher import get_sources_catalog

router = APIRouter(prefix="/articles", tags=["Artigos"])


@router.get(
    "/search",
    response_model=List[Article],
    summary="Busca artigos por query livre",
    description=(
        "Busca artigos no Google News RSS e fontes cadastradas. "
        "Suporta filtros por país, idioma e fonte."
    ),
)
async def search(
    q: str = Query(description="Texto de busca (ex: 'inteligência artificial', 'eleições 2026')"),
    country: Optional[str] = Query(default=None, description="Ex: BR, US, PT"),
    language: Optional[str] = Query(default=None, description="Ex: pt, en, es"),
    source: Optional[str] = Query(default=None, description="Filtro por nome ou domínio da fonte"),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Article]:
    return await search_articles(
        query=q,
        country=country,
        language=language,
        source=source,
        limit=limit,
    )


@router.post(
    "/search",
    response_model=List[Article],
    summary="Busca artigos (via body)",
)
async def search_post(req: ArticleSearchRequest) -> List[Article]:
    return await search_articles(
        query=req.query,
        country=req.country,
        language=req.language,
        source=req.source,
        limit=req.limit,
    )


@router.get(
    "/cached",
    response_model=List[Article],
    summary="Artigos em cache",
    description="Retorna artigos que já foram buscados e estão em cache local.",
)
async def get_cached(
    language: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[Article]:
    return await crud.get_cached_articles(
        language=language,
        country=country,
        limit=limit,
    )


@router.get(
    "/{article_id}",
    response_model=Article,
    summary="Busca artigo pelo ID (hash da URL)",
)
async def get_article(article_id: str) -> Article:
    articles = await crud.get_cached_articles(limit=1000)
    for art in articles:
        if art.id == article_id:
            return art
    raise HTTPException(status_code=404, detail="Artigo não encontrado no cache.")


# ---------------------------------------------------------------------------
# Fontes RSS
# ---------------------------------------------------------------------------

@router.get(
    "/sources/list",
    response_model=List[RSSSource],
    summary="Lista de fontes RSS cadastradas",
    description="Retorna o catálogo de feeds RSS disponíveis, opcionalmente filtrado.",
    tags=["Fontes"],
)
async def list_sources(
    country: Optional[str] = Query(default=None, description="Ex: BR, PT, US"),
    language: Optional[str] = Query(default=None, description="Ex: pt, en, es"),
    category: Optional[str] = Query(default=None, description="Ex: geral, tecnologia, economia, ciencia"),
) -> List[RSSSource]:
    return get_sources_catalog(
        country=country,
        language=language,
        category=category,
    )
