import aiosqlite
from app.config import settings


async def init_db() -> None:
    """Cria as tabelas do banco de dados na inicialização."""
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                url         TEXT NOT NULL,
                source      TEXT,
                published_at TEXT,
                language    TEXT,
                country     TEXT,
                city        TEXT,
                categories  TEXT,   -- JSON array serializado
                keywords    TEXT,   -- JSON array serializado
                summary     TEXT,
                cached_at   TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS trending_topics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword         TEXT NOT NULL,
                country         TEXT NOT NULL,
                language        TEXT NOT NULL,
                interest_score  INTEGER DEFAULT 0,
                related_queries TEXT,   -- JSON array serializado
                fetched_at      TEXT NOT NULL
            )
        """)

        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_lang    ON articles(language)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_country ON articles(country)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_cached  ON articles(cached_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_trends_geo       ON trending_topics(country, language)"
        )
        await db.commit()
