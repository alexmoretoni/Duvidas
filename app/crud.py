"""Operações de leitura/escrita no cache SQLite."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import List, Optional

import aiosqlite

from app.config import settings
from app.schemas import Article, TrendingTopic


def _row_to_article(row: tuple) -> Article:
    return Article(
        id=row[0],
        title=row[1],
        url=row[2],
        source=row[3] or "",
        published_at=datetime.fromisoformat(row[4]) if row[4] else None,
        language=row[5] or "pt",
        country=row[6],
        city=row[7],
        categories=json.loads(row[8]) if row[8] else [],
        keywords=json.loads(row[9]) if row[9] else [],
        summary=row[10],
    )


# ---------------------------------------------------------------------------
# Artigos
# ---------------------------------------------------------------------------

async def save_articles(articles: List[Article]) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        now = datetime.utcnow().isoformat()
        for art in articles:
            await db.execute(
                """
                INSERT OR REPLACE INTO articles
                  (id, title, url, source, published_at, language, country, city,
                   categories, keywords, summary, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    art.id,
                    art.title,
                    art.url,
                    art.source,
                    art.published_at.isoformat() if art.published_at else None,
                    art.language,
                    art.country,
                    art.city,
                    json.dumps(art.categories, ensure_ascii=False),
                    json.dumps(art.keywords, ensure_ascii=False),
                    art.summary,
                    now,
                ),
            )
        await db.commit()


async def get_cached_articles(
    language: Optional[str] = None,
    country: Optional[str] = None,
    limit: int = 100,
) -> List[Article]:
    cutoff = (datetime.utcnow() - timedelta(seconds=settings.cache_ttl)).isoformat()

    conditions = ["cached_at > ?"]
    params: list = [cutoff]

    if language:
        conditions.append("language = ?")
        params.append(language)
    if country:
        conditions.append("country = ?")
        params.append(country)

    where = " AND ".join(conditions)
    params.append(limit)

    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            f"SELECT id,title,url,source,published_at,language,country,city,categories,keywords,summary "
            f"FROM articles WHERE {where} ORDER BY cached_at DESC LIMIT ?",
            params,
        ) as cursor:
            rows = await cursor.fetchall()

    return [_row_to_article(r) for r in rows]


# ---------------------------------------------------------------------------
# Trending Topics
# ---------------------------------------------------------------------------

async def save_trending_topics(topics: List[TrendingTopic]) -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        # Remove trends velhos do mesmo país/idioma antes de inserir novos
        for topic in topics:
            await db.execute(
                "DELETE FROM trending_topics WHERE country=? AND language=?",
                (topic.country, topic.language),
            )
        now = datetime.utcnow().isoformat()
        for t in topics:
            await db.execute(
                """
                INSERT INTO trending_topics
                  (keyword, country, language, interest_score, related_queries, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    t.keyword,
                    t.country,
                    t.language,
                    t.interest_score,
                    json.dumps(t.related_queries, ensure_ascii=False),
                    now,
                ),
            )
        await db.commit()


async def get_cached_trending(
    country: str,
    language: str,
) -> List[TrendingTopic]:
    cutoff = (datetime.utcnow() - timedelta(seconds=settings.cache_ttl)).isoformat()

    async with aiosqlite.connect(settings.db_path) as db:
        async with db.execute(
            """
            SELECT keyword, country, language, interest_score, related_queries, fetched_at
            FROM trending_topics
            WHERE country=? AND language=? AND fetched_at > ?
            ORDER BY interest_score DESC
            """,
            (country, language, cutoff),
        ) as cursor:
            rows = await cursor.fetchall()

    return [
        TrendingTopic(
            keyword=r[0],
            country=r[1],
            language=r[2],
            interest_score=r[3],
            related_queries=json.loads(r[4]) if r[4] else [],
            fetched_at=datetime.fromisoformat(r[5]) if r[5] else None,
        )
        for r in rows
    ]
