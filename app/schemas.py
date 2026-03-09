from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Artigo
# ---------------------------------------------------------------------------

class Article(BaseModel):
    id: str                                  # hash SHA-1 da URL
    title: str
    url: str
    source: str = ""
    published_at: Optional[datetime] = None
    language: str = "pt"
    country: Optional[str] = None            # código ISO 3166-1 alpha-2 (ex: "BR")
    city: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    score: float = 0.0


# ---------------------------------------------------------------------------
# Trending Topics
# ---------------------------------------------------------------------------

class TrendingTopic(BaseModel):
    keyword: str
    country: str
    language: str
    interest_score: int = 0                  # 0-100 normalizado pelo Google Trends
    related_queries: List[str] = Field(default_factory=list)
    fetched_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Requisição de Recomendação
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    keywords: Optional[List[str]] = Field(
        default=None,
        description="Palavras-chave para buscar artigos relacionados",
        examples=[["inteligência artificial", "tecnologia"]],
    )
    urls: Optional[List[str]] = Field(
        default=None,
        description="Domínios/fontes permitidos (ex: ['g1.globo.com', 'folha.uol.com.br'])",
    )
    categories: Optional[List[str]] = Field(
        default=None,
        description="Categorias de interesse (ex: ['tecnologia', 'economia', 'esporte'])",
    )
    cities: Optional[List[str]] = Field(
        default=None,
        description="Cidades para filtrar conteúdo geolocalizado",
    )
    countries: Optional[List[str]] = Field(
        default=None,
        description="Códigos de país ISO 3166-1 (ex: ['BR', 'PT', 'US'])",
    )
    languages: Optional[List[str]] = Field(
        default=None,
        description="Códigos de idioma ISO 639-1 (ex: ['pt', 'en', 'es'])",
    )
    limit: int = Field(default=10, ge=1, le=100)
    use_trends: bool = Field(
        default=True,
        description="Incorporar tendências atuais do Google Trends na pontuação",
    )


# ---------------------------------------------------------------------------
# Resposta de Recomendação
# ---------------------------------------------------------------------------

class RecommendationResponse(BaseModel):
    articles: List[Article]
    trends_used: List[str] = Field(
        default_factory=list,
        description="Keywords trending que influenciaram as recomendações",
    )
    total: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Busca de Artigos
# ---------------------------------------------------------------------------

class ArticleSearchRequest(BaseModel):
    query: str = Field(description="Texto de busca")
    country: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


# ---------------------------------------------------------------------------
# Fonte RSS
# ---------------------------------------------------------------------------

class RSSSource(BaseModel):
    name: str
    url: str
    language: str
    country: str
    category: str = "geral"
