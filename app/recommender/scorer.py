"""
Algoritmo de pontuação de artigos para recomendação.

Fatores considerados:
  1. keyword_match_score  — match das keywords do usuário no texto do artigo
  2. trend_boost          — artigo menciona keywords em alta (Google Trends)
  3. freshness_score      — artigos mais recentes recebem maior pontuação
  4. source_authority     — fontes conhecidas recebem leve bônus
  5. geo_relevance        — match de cidade ou país com os filtros do usuário
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas import Article

# Pesos de cada fator (soma = 1.0)
W_KEYWORD = 0.35
W_TREND   = 0.25
W_FRESH   = 0.20
W_SOURCE  = 0.10
W_GEO     = 0.10

# Fontes com maior autoridade (domínios conhecidos)
AUTHORITY_DOMAINS = {
    "globo.com": 1.0,
    "g1.globo.com": 1.0,
    "folha.uol.com.br": 1.0,
    "estadao.com.br": 1.0,
    "agenciabrasil.ebc.com.br": 1.0,
    "bbci.co.uk": 0.95,
    "bbc.com": 0.95,
    "reuters.com": 0.95,
    "tecmundo.com.br": 0.90,
    "canaltech.com.br": 0.90,
    "techtudo.com.br": 0.88,
    "exame.com": 0.88,
    "infomoney.com.br": 0.85,
    "valor.globo.com": 0.88,
    "techcrunch.com": 0.90,
    "theverge.com": 0.88,
    "cnn.com": 0.85,
    "elpais.com": 0.88,
    "dw.com": 0.85,
    "nature.com": 0.95,
    "sciencedaily.com": 0.85,
}
DEFAULT_AUTHORITY = 0.60


def _normalize(text: str) -> str:
    return text.lower()


def _article_searchable_text(article: Article) -> str:
    parts = [
        article.title or "",
        article.summary or "",
        " ".join(article.keywords),
        " ".join(article.categories),
    ]
    return _normalize(" ".join(parts))


def keyword_match_score(article: Article, keywords: List[str]) -> float:
    """Score baseado na frequência de keywords no texto do artigo."""
    if not keywords:
        return 0.5  # score neutro quando sem keywords
    text = _article_searchable_text(article)
    matches = sum(1 for kw in keywords if _normalize(kw) in text)
    return min(matches / len(keywords), 1.0)


def trend_boost_score(article: Article, trending_keywords: List[str]) -> float:
    """Score baseado em quantos trending keywords aparecem no artigo."""
    if not trending_keywords:
        return 0.0
    text = _article_searchable_text(article)
    matches = sum(1 for kw in trending_keywords if _normalize(kw) in text)
    # Escala logarítmica: 1 match → 0.5, 5 matches → ~1.0
    if matches == 0:
        return 0.0
    return min(math.log(matches + 1) / math.log(len(trending_keywords) + 1), 1.0)


def freshness_score(article: Article, now: Optional[datetime] = None) -> float:
    """
    Decaimento exponencial por idade.
    Artigo de agora = 1.0, de 24h atrás ≈ 0.5, de 7 dias atrás ≈ 0.05.
    """
    if article.published_at is None:
        return 0.3  # score baixo para artigos sem data

    if now is None:
        now = datetime.now(timezone.utc)

    pub = article.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)

    age_hours = (now - pub).total_seconds() / 3600
    age_hours = max(0, age_hours)

    # Meia-vida de 24 horas
    return math.exp(-0.693 * age_hours / 24)


def source_authority_score(article: Article) -> float:
    """Score baseado na autoridade reconhecida da fonte."""
    from urllib.parse import urlparse
    try:
        domain = urlparse(article.url).netloc.replace("www.", "").lower()
    except Exception:
        return DEFAULT_AUTHORITY

    # Busca por sufixo do domínio
    for known, score in AUTHORITY_DOMAINS.items():
        if domain.endswith(known) or known.endswith(domain):
            return score
    return DEFAULT_AUTHORITY


def geo_relevance_score(
    article: Article,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
) -> float:
    """Score de relevância geográfica."""
    if not countries and not cities:
        return 0.5  # neutro quando sem filtros geográficos

    score = 0.0
    matches = 0
    total = 0

    if countries:
        total += 1
        if article.country and article.country.upper() in [c.upper() for c in countries]:
            score += 1.0
            matches += 1
        else:
            # Verifica no texto
            text = _article_searchable_text(article)
            country_names = {
                "BR": ["brasil", "brazil", "brasileiro"],
                "PT": ["portugal", "português"],
                "US": ["estados unidos", "united states", "america"],
                "GB": ["reino unido", "united kingdom", "britain"],
                "AR": ["argentina", "argentino"],
                "MX": ["méxico", "mexico", "mexicano"],
            }
            for c in countries:
                for name in country_names.get(c.upper(), []):
                    if name in text:
                        score += 0.5
                        break

    if cities:
        total += 1
        text = _article_searchable_text(article)
        if any(_normalize(city) in text for city in cities):
            score += 1.0
            matches += 1

    if total == 0:
        return 0.5
    return min(score / total, 1.0)


def score_article(
    article: Article,
    *,
    user_keywords: Optional[List[str]] = None,
    trending_keywords: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    now: Optional[datetime] = None,
) -> float:
    """Calcula a pontuação final ponderada de um artigo."""
    kw = keyword_match_score(article, user_keywords or [])
    tr = trend_boost_score(article, trending_keywords or [])
    fr = freshness_score(article, now)
    sa = source_authority_score(article)
    ge = geo_relevance_score(article, countries, cities)

    total = (
        W_KEYWORD * kw
        + W_TREND   * tr
        + W_FRESH   * fr
        + W_SOURCE  * sa
        + W_GEO     * ge
    )
    return round(total, 4)


def rank_articles(
    articles: List[Article],
    *,
    user_keywords: Optional[List[str]] = None,
    trending_keywords: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
) -> List[Article]:
    """Pontua e ordena artigos do mais relevante para o menos."""
    now = datetime.now(timezone.utc)
    for art in articles:
        art.score = score_article(
            art,
            user_keywords=user_keywords,
            trending_keywords=trending_keywords,
            countries=countries,
            cities=cities,
            now=now,
        )
    return sorted(articles, key=lambda a: a.score, reverse=True)
