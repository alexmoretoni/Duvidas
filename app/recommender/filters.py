"""
Filtros de artigos por idioma, país, cidade, keywords, domínio e categoria.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urlparse

from app.schemas import Article

logger = logging.getLogger(__name__)


def _contains_any(text: str, terms: List[str]) -> bool:
    text_lower = text.lower()
    return any(term.lower() in text_lower for term in terms)


def _article_text(article: Article) -> str:
    parts = [article.title or "", article.summary or ""]
    parts.extend(article.keywords)
    parts.extend(article.categories)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Filtros individuais
# ---------------------------------------------------------------------------

def filter_by_language(articles: List[Article], languages: List[str]) -> List[Article]:
    if not languages:
        return articles
    langs = [lang.lower() for lang in languages]
    return [a for a in articles if a.language.lower() in langs]


def filter_by_country(articles: List[Article], countries: List[str]) -> List[Article]:
    if not countries:
        return articles
    codes = [c.upper() for c in countries]
    return [a for a in articles if a.country and a.country.upper() in codes]


def filter_by_city(articles: List[Article], cities: List[str]) -> List[Article]:
    """
    Filtra por cidade: verifica no campo city do artigo e no texto completo.
    Artigos sem city_field mas que mencionam a cidade no texto também passam.
    """
    if not cities:
        return articles
    result = []
    for art in articles:
        city_match = art.city and _contains_any(art.city, cities)
        text_match = _contains_any(_article_text(art), cities)
        if city_match or text_match:
            result.append(art)
    return result


def filter_by_keywords(articles: List[Article], keywords: List[str]) -> List[Article]:
    if not keywords:
        return articles
    return [
        a for a in articles
        if _contains_any(_article_text(a), keywords)
    ]


def filter_by_domain(articles: List[Article], urls: List[str]) -> List[Article]:
    """
    Filtra por domínio/URL.
    Aceita domínios parciais: 'g1.globo.com' ou 'globo.com' ambos funcionam.
    """
    if not urls:
        return articles
    # Normaliza: remove 'www.' e protocolos
    allowed = []
    for u in urls:
        domain = u.lower()
        if "://" in domain:
            domain = urlparse(domain).netloc
        domain = domain.replace("www.", "")
        allowed.append(domain)

    result = []
    for art in articles:
        try:
            art_domain = urlparse(art.url).netloc.replace("www.", "").lower()
            if any(a in art_domain or art_domain in a for a in allowed):
                result.append(art)
        except Exception:
            pass
    return result


def filter_by_category(articles: List[Article], categories: List[str]) -> List[Article]:
    if not categories:
        return articles
    cats = [c.lower() for c in categories]
    result = []
    for art in articles:
        art_cats = [c.lower() for c in art.categories]
        text = _article_text(art).lower()
        if any(c in art_cats or c in text for c in cats):
            result.append(art)
    return result


# ---------------------------------------------------------------------------
# Aplicação em cadeia
# ---------------------------------------------------------------------------

def apply_filters(
    articles: List[Article],
    *,
    languages: Optional[List[str]] = None,
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    urls: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
) -> List[Article]:
    """
    Aplica todos os filtros em sequência.
    Filtros com valor None ou lista vazia são ignorados.
    """
    result = articles

    if languages:
        result = filter_by_language(result, languages)
        logger.debug("Após filtro idioma %s: %d artigos", languages, len(result))

    if countries:
        before = len(result)
        filtered = filter_by_country(result, countries)
        # Se o filtro por país eliminar tudo, manter os originais (RSS pode não ter metadata)
        result = filtered if filtered else result
        logger.debug("Após filtro país %s: %d artigos (antes: %d)", countries, len(result), before)

    if cities:
        result = filter_by_city(result, cities)
        logger.debug("Após filtro cidade %s: %d artigos", cities, len(result))

    if urls:
        result = filter_by_domain(result, urls)
        logger.debug("Após filtro domínio %s: %d artigos", urls, len(result))

    if categories:
        before = len(result)
        filtered = filter_by_category(result, categories)
        result = filtered if filtered else result
        logger.debug("Após filtro categoria %s: %d artigos (antes: %d)", categories, len(result), before)

    if keywords:
        before = len(result)
        filtered = filter_by_keywords(result, keywords)
        # Se o filtro por keyword eliminar tudo, retornar os artigos sem esse filtro
        # (artigos de trends podem ser relevantes mesmo sem match direto)
        result = filtered if filtered else result
        logger.debug("Após filtro keyword %s: %d artigos (antes: %d)", keywords, len(result), before)

    return result
