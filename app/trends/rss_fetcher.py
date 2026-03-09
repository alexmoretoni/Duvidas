"""
Busca de artigos via feeds RSS públicos e Google News RSS.

Não requer nenhuma API key.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import trafilatura

from app.schemas import Article, RSSSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Catálogo de fontes RSS por país/idioma
# ---------------------------------------------------------------------------

RSS_SOURCES: List[RSSSource] = [
    # Brasil — geral
    RSSSource(name="G1", url="https://g1.globo.com/rss/g1/", language="pt", country="BR", category="geral"),
    RSSSource(name="Folha de S.Paulo", url="https://feeds.folha.uol.com.br/poder/rss091.xml", language="pt", country="BR", category="geral"),
    RSSSource(name="Estadão", url="https://www.estadao.com.br/rss/ultimas.xml", language="pt", country="BR", category="geral"),
    RSSSource(name="Agência Brasil", url="https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml", language="pt", country="BR", category="geral"),
    RSSSource(name="UOL Notícias", url="https://rss.uol.com.br/feed/noticias.xml", language="pt", country="BR", category="geral"),
    # Brasil — tecnologia
    RSSSource(name="Tecmundo", url="https://www.tecmundo.com.br/rss", language="pt", country="BR", category="tecnologia"),
    RSSSource(name="Canaltech", url="https://canaltech.com.br/rss/", language="pt", country="BR", category="tecnologia"),
    RSSSource(name="TechTudo", url="https://www.techtudo.com.br/rss/all.xml", language="pt", country="BR", category="tecnologia"),
    # Brasil — economia
    RSSSource(name="Exame", url="https://exame.com/feed/", language="pt", country="BR", category="economia"),
    RSSSource(name="InfoMoney", url="https://www.infomoney.com.br/feed/", language="pt", country="BR", category="economia"),
    RSSSource(name="Valor Econômico", url="https://valor.globo.com/rss/valorecon/", language="pt", country="BR", category="economia"),
    # Portugal
    RSSSource(name="Público", url="https://feeds.feedburner.com/PublicoRSS", language="pt", country="PT", category="geral"),
    RSSSource(name="Jornal de Negócios", url="https://www.jornaldenegocios.pt/rss", language="pt", country="PT", category="economia"),
    # BBC (multilíngue)
    RSSSource(name="BBC Brasil", url="https://feeds.bbci.co.uk/portuguese/rss.xml", language="pt", country="BR", category="geral"),
    RSSSource(name="BBC News", url="https://feeds.bbci.co.uk/news/rss.xml", language="en", country="GB", category="geral"),
    RSSSource(name="BBC Technology", url="https://feeds.bbci.co.uk/news/technology/rss.xml", language="en", country="GB", category="tecnologia"),
    # Reuters
    RSSSource(name="Reuters", url="https://feeds.reuters.com/reuters/topNews", language="en", country="US", category="geral"),
    RSSSource(name="Reuters Technology", url="https://feeds.reuters.com/reuters/technologyNews", language="en", country="US", category="tecnologia"),
    # El País
    RSSSource(name="El País Brasil", url="https://brasil.elpais.com/arc/outboundfeeds/rss/", language="pt", country="BR", category="geral"),
    RSSSource(name="El País España", url="https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", language="es", country="ES", category="geral"),
    # Espanhol — América Latina
    RSSSource(name="Infobae", url="https://www.infobae.com/feeds/rss/", language="es", country="AR", category="geral"),
    RSSSource(name="La Nación AR", url="https://www.lanacion.com.ar/arc/outboundfeeds/rss/", language="es", country="AR", category="geral"),
    # Inglês — EUA/global
    RSSSource(name="TechCrunch", url="https://techcrunch.com/feed/", language="en", country="US", category="tecnologia"),
    RSSSource(name="The Verge", url="https://www.theverge.com/rss/index.xml", language="en", country="US", category="tecnologia"),
    RSSSource(name="CNN", url="http://rss.cnn.com/rss/cnn_topstories.rss", language="en", country="US", category="geral"),
    RSSSource(name="NPR News", url="https://feeds.npr.org/1001/rss.xml", language="en", country="US", category="geral"),
    # Ciência
    RSSSource(name="Nature", url="https://www.nature.com/nature.rss", language="en", country="US", category="ciencia"),
    RSSSource(name="Science Daily", url="https://www.sciencedaily.com/rss/all.xml", language="en", country="US", category="ciencia"),
    # Alemão
    RSSSource(name="Deutsche Welle PT", url="https://rss.dw.com/rdf/rss-bra-all", language="pt", country="BR", category="geral"),
    RSSSource(name="Spiegel Online", url="https://www.spiegel.de/schlagzeilen/index.rss", language="de", country="DE", category="geral"),
    # Francês
    RSSSource(name="Le Monde", url="https://www.lemonde.fr/rss/une.xml", language="fr", country="FR", category="geral"),
]


# ---------------------------------------------------------------------------
# Google News RSS (sem API key, baseado em URL parametrizada)
# ---------------------------------------------------------------------------

_GNEWS_BASE = "https://news.google.com/rss"

_COUNTRY_LANG_MAP: Dict[str, Dict[str, str]] = {
    "BR": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
    "PT": {"hl": "pt-PT", "gl": "PT", "ceid": "PT:pt"},
    "US": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "GB": {"hl": "en-GB", "gl": "GB", "ceid": "GB:en"},
    "DE": {"hl": "de-DE", "gl": "DE", "ceid": "DE:de"},
    "FR": {"hl": "fr-FR", "gl": "FR", "ceid": "FR:fr"},
    "ES": {"hl": "es-ES", "gl": "ES", "ceid": "ES:es"},
    "AR": {"hl": "es-419", "gl": "AR", "ceid": "AR:es-419"},
    "MX": {"hl": "es-419", "gl": "MX", "ceid": "MX:es-419"},
    "JP": {"hl": "ja-JP", "gl": "JP", "ceid": "JP:ja"},
}


def google_news_rss_url(country: str, language: str, query: Optional[str] = None) -> str:
    params = _COUNTRY_LANG_MAP.get(country, _COUNTRY_LANG_MAP["BR"])
    hl = params["hl"]
    gl = params["gl"]
    ceid = params["ceid"]
    if query:
        encoded = query.replace(" ", "+")
        return f"{_GNEWS_BASE}/search?q={encoded}&hl={hl}&gl={gl}&ceid={ceid}"
    return f"{_GNEWS_BASE}?hl={hl}&gl={gl}&ceid={ceid}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_id(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _parse_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    for attr in ("published", "updated", "created"):
        raw = entry.get(attr)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                try:
                    return datetime.fromisoformat(raw.rstrip("Z"))
                except Exception:
                    pass
    return None


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _entry_to_article(entry: feedparser.FeedParserDict, source: RSSSource) -> Optional[Article]:
    url = entry.get("link", "")
    title = _clean_text(entry.get("title", ""))
    if not url or not title:
        return None

    summary_raw = entry.get("summary", "") or entry.get("description", "")
    summary = _clean_text(summary_raw)[:500] if summary_raw else None

    tags = [t.get("term", "") for t in entry.get("tags", []) if t.get("term")]
    keywords = [kw for kw in tags if kw]

    return Article(
        id=_make_id(url),
        title=title,
        url=url,
        source=source.name,
        published_at=_parse_date(entry),
        language=source.language,
        country=source.country,
        categories=[source.category],
        keywords=keywords,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Fetch individual feed (síncrono — roda em thread pool)
# ---------------------------------------------------------------------------

def _fetch_feed_sync(source: RSSSource, max_items: int = 30) -> List[Article]:
    articles: List[Article] = []
    try:
        feed = feedparser.parse(source.url)
        for entry in feed.entries[:max_items]:
            art = _entry_to_article(entry, source)
            if art:
                articles.append(art)
    except Exception as exc:
        logger.debug("Erro ao ler feed %s: %s", source.name, exc)
    return articles


def _fetch_gnews_sync(
    country: str,
    language: str,
    query: Optional[str],
    max_items: int = 30,
) -> List[Article]:
    url = google_news_rss_url(country, language, query)
    lang_map = {
        "pt": "pt", "en": "en", "es": "es", "de": "de", "fr": "fr",
        "pt-BR": "pt", "pt-PT": "pt",
    }
    lang_code = lang_map.get(language, language[:2])
    source = RSSSource(
        name="Google News",
        url=url,
        language=lang_code,
        country=country,
        category="geral",
    )
    return _fetch_feed_sync(source, max_items)


# ---------------------------------------------------------------------------
# API pública (assíncrona)
# ---------------------------------------------------------------------------

async def fetch_google_news(
    country: str = "BR",
    language: str = "pt",
    query: Optional[str] = None,
    max_items: int = 30,
) -> List[Article]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _fetch_gnews_sync, country, language, query, max_items
    )


async def fetch_rss_source(source: RSSSource, max_items: int = 30) -> List[Article]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_feed_sync, source, max_items)


async def fetch_multiple_sources(
    sources: List[RSSSource],
    max_items_each: int = 20,
) -> List[Article]:
    """Busca todos os feeds em paralelo."""
    tasks = [fetch_rss_source(s, max_items_each) for s in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    articles: List[Article] = []
    for res in results:
        if isinstance(res, list):
            articles.extend(res)
    return articles


async def fetch_articles_for_countries(
    countries: List[str],
    languages: List[str],
    keywords: Optional[List[str]] = None,
    max_items_each: int = 20,
) -> List[Article]:
    """
    Combina:
      1. Google News RSS para cada par país/idioma (com query opcional)
      2. Feeds RSS do catálogo filtrados por país/idioma
    """
    query = " ".join(keywords) if keywords else None
    tasks = []

    # Google News RSS
    for country in countries:
        lang = languages[0] if languages else "pt"
        tasks.append(fetch_google_news(country, lang, query, max_items_each))

    # Fontes do catálogo que batem com país/idioma
    matching = [
        s for s in RSS_SOURCES
        if (not countries or s.country in countries)
        and (not languages or s.language in languages)
    ]
    for source in matching:
        tasks.append(fetch_rss_source(source, max_items_each))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    articles: List[Article] = []
    seen: set = set()
    for res in results:
        if isinstance(res, list):
            for art in res:
                if art.id not in seen:
                    seen.add(art.id)
                    articles.append(art)
    return articles


def get_sources_catalog(
    country: Optional[str] = None,
    language: Optional[str] = None,
    category: Optional[str] = None,
) -> List[RSSSource]:
    """Retorna fontes do catálogo filtradas pelos parâmetros."""
    sources = RSS_SOURCES
    if country:
        sources = [s for s in sources if s.country == country]
    if language:
        sources = [s for s in sources if s.language == language]
    if category:
        sources = [s for s in sources if s.category == category]
    return sources
