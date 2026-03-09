"""
Motor principal de recomendação.

Pipeline:
  1. Verificar cache SQLite (TTL configurável)
  2. Buscar trending topics (Google Trends)
  3. Buscar artigos (Google News RSS + feeds do catálogo)
  4. Aplicar filtros (idioma, país, cidade, keyword, domínio, categoria)
  5. Pontuar e ordenar artigos
  6. Salvar resultados no cache
  7. Retornar top N artigos + metadata
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from app import crud
from app.config import settings
from app.recommender.filters import apply_filters
from app.recommender.scorer import rank_articles
from app.schemas import Article, RecommendationRequest, RecommendationResponse, TrendingTopic
from app.trends.google_trends import get_trending_topics
from app.trends.rss_fetcher import fetch_articles_for_countries, fetch_google_news

logger = logging.getLogger(__name__)


async def _get_trends(
    countries: List[str],
    language: str,
) -> List[TrendingTopic]:
    """Busca trends: primeiro do cache, depois do Google Trends."""
    country = countries[0] if countries else settings.default_country

    # Tenta cache
    cached = await crud.get_cached_trending(country, language)
    if cached:
        logger.info("Trends do cache: %d topics para %s/%s", len(cached), country, language)
        return cached

    # Busca no Google Trends
    try:
        topics = await get_trending_topics(country=country, language=language)
        if topics:
            await crud.save_trending_topics(topics)
            logger.info("Trends do Google: %d topics para %s/%s", len(topics), country, language)
        return topics
    except Exception as exc:
        logger.warning("Falha ao buscar trends: %s", exc)
        return []


async def _get_articles(
    req: RecommendationRequest,
    trending_keywords: List[str],
) -> List[Article]:
    """
    Busca artigos de múltiplas fontes em paralelo.
    Combina Google News RSS + feeds do catálogo.
    """
    countries = req.countries or [settings.default_country]
    languages = req.languages or [settings.default_language]

    # Combina keywords do usuário com top 3 trends para enriquecer a busca
    search_keywords = list(req.keywords or [])
    search_keywords.extend(trending_keywords[:3])

    # Busca de fontes múltiplas em paralelo
    tasks = []

    # 1. Artigos dos países solicitados via feeds do catálogo + Google News RSS
    tasks.append(
        fetch_articles_for_countries(
            countries=countries,
            languages=languages,
            keywords=search_keywords or None,
            max_items_each=20,
        )
    )

    # 2. Busca adicional no Google News com cada keyword importante
    for kw in (req.keywords or [])[:3]:
        for country in countries[:2]:
            lang = languages[0] if languages else "pt"
            tasks.append(fetch_google_news(country=country, language=lang, query=kw, max_items=15))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: List[Article] = []
    seen: set = set()
    for res in results:
        if isinstance(res, list):
            for art in res:
                if art.id not in seen:
                    seen.add(art.id)
                    articles.append(art)

    logger.info("Total de artigos coletados (antes dos filtros): %d", len(articles))
    return articles


async def recommend(req: RecommendationRequest) -> RecommendationResponse:
    """
    Pipeline completo de recomendação.
    """
    countries = req.countries or [settings.default_country]
    languages = req.languages or [settings.default_language]
    language = languages[0]

    # --- Passo 1: Trending Topics ---
    trending_topics: List[TrendingTopic] = []
    trending_keywords: List[str] = []

    if req.use_trends:
        trending_topics = await _get_trends(countries, language)
        trending_keywords = [t.keyword for t in trending_topics]

    # --- Passo 2: Buscar artigos ---
    articles = await _get_articles(req, trending_keywords)

    # --- Passo 3: Aplicar filtros ---
    filtered = apply_filters(
        articles,
        languages=languages if req.languages else None,
        countries=countries if req.countries else None,
        cities=req.cities,
        keywords=req.keywords,
        urls=req.urls,
        categories=req.categories,
    )

    # --- Passo 4: Pontuar e ordenar ---
    ranked = rank_articles(
        filtered,
        user_keywords=req.keywords,
        trending_keywords=trending_keywords,
        countries=countries,
        cities=req.cities,
    )

    # --- Passo 5: Limitar e salvar cache ---
    top = ranked[: req.limit]
    if top:
        asyncio.create_task(_save_to_cache(top))

    # Keywords trending relevantes (que aparecem nos top artigos)
    top_text = " ".join(a.title + " " + (a.summary or "") for a in top).lower()
    trends_used = [kw for kw in trending_keywords[:10] if kw.lower() in top_text]

    return RecommendationResponse(
        articles=top,
        trends_used=trends_used,
        total=len(top),
    )


async def _save_to_cache(articles: List[Article]) -> None:
    try:
        await crud.save_articles(articles)
    except Exception as exc:
        logger.debug("Erro ao salvar cache: %s", exc)


async def search_articles(
    query: str,
    country: Optional[str] = None,
    language: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 20,
) -> List[Article]:
    """
    Busca direta de artigos via Google News RSS com uma query livre.
    """
    _country = country or settings.default_country
    _language = language or settings.default_language

    # Tenta cache primeiro
    cached = await crud.get_cached_articles(language=_language, country=_country, limit=limit * 3)
    if cached:
        from app.recommender.scorer import rank_articles as _rank
        ranked = _rank(cached, user_keywords=query.split())
        if source:
            ranked = [a for a in ranked if source.lower() in a.source.lower()]
        return ranked[:limit]

    # Busca ao vivo
    articles = await fetch_google_news(
        country=_country,
        language=_language,
        query=query,
        max_items=limit,
    )

    if source:
        articles = [a for a in articles if source.lower() in a.source.lower()]

    from app.recommender.scorer import rank_articles as _rank
    return _rank(articles, user_keywords=query.split())[:limit]
