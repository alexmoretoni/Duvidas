"""
Integração com Google Trends via pytrends (sem API key).

Limitações:
  - Google pode aplicar rate-limit; use TRENDS_SLEEP >= 60 segundos.
  - Dados são normalizados (0-100), não volumes absolutos.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, List

from pytrends.request import TrendReq

from app.config import settings
from app.schemas import TrendingTopic

logger = logging.getLogger(__name__)

# Mapeamento país → locale do Google Trends
_GEO_MAP: Dict[str, str] = {
    "BR": "BR",
    "PT": "PT",
    "US": "US",
    "GB": "GB",
    "DE": "DE",
    "FR": "FR",
    "ES": "ES",
    "AR": "AR",
    "MX": "MX",
    "CO": "CO",
}

# Mapeamento país → hl (locale para pytrends)
_HL_MAP: Dict[str, str] = {
    "BR": "pt-BR",
    "PT": "pt-PT",
    "US": "en-US",
    "GB": "en-GB",
    "DE": "de-DE",
    "FR": "fr-FR",
    "ES": "es-ES",
    "AR": "es-AR",
    "MX": "es-MX",
    "CO": "es-CO",
}


def _build_client(country: str) -> TrendReq:
    hl = _HL_MAP.get(country, "pt-BR")
    return TrendReq(hl=hl, tz=180, timeout=(10, 25), retries=2, backoff_factor=0.5)


def _fetch_trending_sync(country: str, language: str) -> List[TrendingTopic]:
    """Executa chamadas síncronas ao pytrends (roda em thread pool)."""
    geo = _GEO_MAP.get(country, country)
    pytrends = _build_client(country)
    topics: List[TrendingTopic] = []

    try:
        # 1. Trending searches (realtime)
        trending_df = pytrends.trending_searches(pn=_country_to_pn(country))
        keywords = trending_df[0].tolist()[:20]

        for kw in keywords:
            topics.append(
                TrendingTopic(
                    keyword=kw,
                    country=country,
                    language=language,
                    interest_score=50,  # valor base; será refinado abaixo
                    related_queries=[],
                )
            )

        time.sleep(2)

        # 2. Para os top 5 keywords, buscar interest_over_time + related_queries
        top_kws = keywords[:5]
        if top_kws:
            pytrends.build_payload(top_kws, timeframe="now 1-d", geo=geo)
            time.sleep(1)

            try:
                iot = pytrends.interest_over_time()
                if not iot.empty:
                    for kw in top_kws:
                        if kw in iot.columns:
                            score = int(iot[kw].mean())
                            for t in topics:
                                if t.keyword == kw:
                                    t.interest_score = score
            except Exception as exc:
                logger.debug("interest_over_time error: %s", exc)

            time.sleep(2)

            try:
                related = pytrends.related_queries()
                for kw in top_kws:
                    if kw in related and related[kw].get("top") is not None:
                        rq_df = related[kw]["top"]
                        rq = rq_df["query"].tolist()[:5] if rq_df is not None else []
                        for t in topics:
                            if t.keyword == kw:
                                t.related_queries = rq
            except Exception as exc:
                logger.debug("related_queries error: %s", exc)

    except Exception as exc:
        logger.warning("Google Trends falhou para %s: %s", country, exc)

    return topics


def _country_to_pn(country: str) -> str:
    """Converte código de país para o parâmetro 'pn' do trending_searches."""
    mapping = {
        "BR": "brazil",
        "PT": "portugal",
        "US": "united_states",
        "GB": "united_kingdom",
        "DE": "germany",
        "FR": "france",
        "ES": "spain",
        "AR": "argentina",
        "MX": "mexico",
        "CO": "colombia",
        "JP": "japan",
        "AU": "australia",
        "IN": "india",
    }
    return mapping.get(country, "brazil")


async def get_trending_topics(
    country: str = "BR",
    language: str = "pt",
) -> List[TrendingTopic]:
    """
    Busca trending topics do Google Trends de forma assíncrona.
    Roda as chamadas síncronas do pytrends em uma thread pool separada.
    """
    loop = asyncio.get_event_loop()
    topics = await loop.run_in_executor(
        None, _fetch_trending_sync, country, language
    )
    return topics


async def get_related_queries(
    keywords: List[str],
    country: str = "BR",
) -> Dict[str, List[str]]:
    """Retorna queries relacionadas para uma lista de keywords."""
    geo = _GEO_MAP.get(country, country)
    pytrends = _build_client(country)
    result: Dict[str, List[str]] = {}

    def _fetch() -> Dict[str, List[str]]:
        try:
            pytrends.build_payload(keywords[:5], timeframe="now 7-d", geo=geo)
            time.sleep(1)
            related = pytrends.related_queries()
            for kw in keywords[:5]:
                if kw in related and related[kw].get("top") is not None:
                    df = related[kw]["top"]
                    result[kw] = df["query"].tolist()[:5] if df is not None else []
                else:
                    result[kw] = []
        except Exception as exc:
            logger.warning("related_queries error: %s", exc)
        return result

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch)
