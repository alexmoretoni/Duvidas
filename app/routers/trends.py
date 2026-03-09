from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from app import crud
from app.config import settings
from app.schemas import TrendingTopic
from app.trends.google_trends import get_trending_topics

router = APIRouter(prefix="/trends", tags=["Trends"])


@router.get(
    "",
    response_model=List[TrendingTopic],
    summary="Trending topics atuais",
    description=(
        "Retorna os tópicos em alta para o par país/idioma informado. "
        "Dados são cacheados por CACHE_TTL segundos para respeitar o rate-limit do Google Trends."
    ),
)
async def get_trends(
    country: str = Query(default=settings.default_country, description="Código de país ISO 3166-1 (ex: BR, US, PT)"),
    language: str = Query(default=settings.default_language, description="Código de idioma ISO 639-1 (ex: pt, en, es)"),
    force_refresh: bool = Query(default=False, description="Ignorar cache e buscar dados frescos"),
) -> List[TrendingTopic]:
    if not force_refresh:
        cached = await crud.get_cached_trending(country.upper(), language.lower())
        if cached:
            return cached

    topics = await get_trending_topics(country=country.upper(), language=language.lower())
    if topics:
        await crud.save_trending_topics(topics)
    return topics


@router.get(
    "/keywords",
    response_model=List[str],
    summary="Keywords em alta",
    description="Retorna apenas a lista de palavras-chave trending (sem metadata).",
)
async def get_trending_keywords(
    country: str = Query(default=settings.default_country),
    language: str = Query(default=settings.default_language),
) -> List[str]:
    cached = await crud.get_cached_trending(country.upper(), language.lower())
    if cached:
        return [t.keyword for t in cached]

    topics = await get_trending_topics(country=country.upper(), language=language.lower())
    if topics:
        await crud.save_trending_topics(topics)
    return [t.keyword for t in topics]


@router.get(
    "/countries",
    response_model=List[dict],
    summary="Países suportados para análise de trends",
)
async def list_supported_countries() -> List[dict]:
    return [
        {"code": "BR", "name": "Brasil", "language": "pt"},
        {"code": "PT", "name": "Portugal", "language": "pt"},
        {"code": "US", "name": "Estados Unidos", "language": "en"},
        {"code": "GB", "name": "Reino Unido", "language": "en"},
        {"code": "DE", "name": "Alemanha", "language": "de"},
        {"code": "FR", "name": "França", "language": "fr"},
        {"code": "ES", "name": "Espanha", "language": "es"},
        {"code": "AR", "name": "Argentina", "language": "es"},
        {"code": "MX", "name": "México", "language": "es"},
        {"code": "JP", "name": "Japão", "language": "ja"},
        {"code": "AU", "name": "Austrália", "language": "en"},
        {"code": "IN", "name": "Índia", "language": "en"},
        {"code": "CO", "name": "Colômbia", "language": "es"},
    ]
