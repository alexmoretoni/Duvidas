#!/usr/bin/env python3
"""
Trending Article Recommender — Interface de linha de comando (CLI)

Uso:
    python cli.py --help
    python cli.py trends
    python cli.py search "inteligência artificial"
    python cli.py recommend --keywords "IA" --country BR --limit 10
    python cli.py serve
"""

from __future__ import annotations

import asyncio
import json
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

app = typer.Typer(
    name="trends-recommender",
    help="Sistema de análise de trends e recomendação de artigos.",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Executa uma coroutine em loop síncrono (para uso no CLI)."""
    return asyncio.run(coro)


def _setup_db():
    from app.database import init_db
    _run(init_db())


def _print_articles(articles, title: str = "Artigos Recomendados"):
    if not articles:
        console.print("[yellow]Nenhum artigo encontrado.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", style="cyan", width=6)
    table.add_column("Título", style="bold", max_width=55)
    table.add_column("Fonte", style="green", width=18)
    table.add_column("Idioma", width=7)
    table.add_column("País", width=5)
    table.add_column("Data", width=12)

    for i, art in enumerate(articles, 1):
        pub = art.published_at.strftime("%d/%m %H:%M") if art.published_at else "—"
        score = f"{art.score:.3f}" if art.score else "—"
        table.add_row(
            str(i),
            score,
            art.title[:55],
            art.source[:18],
            art.language,
            art.country or "—",
            pub,
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(articles)} artigos[/dim]")


# ---------------------------------------------------------------------------
# Comando: trends
# ---------------------------------------------------------------------------

@app.command()
def trends(
    country: str = typer.Option("BR", "--country", "-c", help="Código de país ISO 3166-1 (ex: BR, US, PT)"),
    language: str = typer.Option("pt", "--language", "-l", help="Código de idioma ISO 639-1 (ex: pt, en, es)"),
    output_json: bool = typer.Option(False, "--json", help="Exibir saída em formato JSON"),
):
    """Exibe os tópicos em alta do Google Trends para um país/idioma."""
    _setup_db()

    console.print(f"[bold]Buscando trends para {country}/{language}...[/bold]")

    from app.trends.google_trends import get_trending_topics
    topics = _run(get_trending_topics(country=country.upper(), language=language.lower()))

    if output_json:
        print(json.dumps([t.model_dump(mode="json") for t in topics], ensure_ascii=False, indent=2))
        return

    if not topics:
        console.print("[yellow]Nenhum trend encontrado. Tente novamente em alguns segundos.[/yellow]")
        return

    table = Table(title=f"Trends em Alta — {country}/{language}", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Keyword", style="bold magenta", min_width=25)
    table.add_column("Score", style="cyan", width=8)
    table.add_column("Queries Relacionadas", style="dim")

    for i, t in enumerate(topics[:20], 1):
        related = ", ".join(t.related_queries[:3]) if t.related_queries else "—"
        table.add_row(str(i), t.keyword, str(t.interest_score), related)

    console.print(table)


# ---------------------------------------------------------------------------
# Comando: search
# ---------------------------------------------------------------------------

@app.command()
def search(
    query: str = typer.Argument(help="Texto de busca (ex: 'inteligência artificial')"),
    country: Optional[str] = typer.Option(None, "--country", "-c", help="Ex: BR, US, PT"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Ex: pt, en, es"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filtro por fonte/domínio"),
    limit: int = typer.Option(15, "--limit", "-n", help="Número máximo de resultados"),
    output_json: bool = typer.Option(False, "--json", help="Saída em JSON"),
):
    """Busca artigos por uma query livre no Google News RSS e fontes cadastradas."""
    _setup_db()

    console.print(f"[bold]Buscando: '{query}'...[/bold]")

    from app.recommender.engine import search_articles
    articles = _run(search_articles(
        query=query,
        country=country,
        language=language,
        source=source,
        limit=limit,
    ))

    if output_json:
        print(json.dumps([a.model_dump(mode="json") for a in articles], ensure_ascii=False, indent=2))
        return

    _print_articles(articles, title=f"Resultados para '{query}'")


# ---------------------------------------------------------------------------
# Comando: recommend
# ---------------------------------------------------------------------------

@app.command()
def recommend(
    keywords: Optional[List[str]] = typer.Option(None, "--keywords", "-k", help="Keywords separadas por vírgula"),
    countries: Optional[List[str]] = typer.Option(None, "--country", "-c", help="Países (ex: BR PT US)"),
    languages: Optional[List[str]] = typer.Option(None, "--language", "-l", help="Idiomas (ex: pt en)"),
    cities: Optional[List[str]] = typer.Option(None, "--city", help="Cidades para filtro geográfico"),
    categories: Optional[List[str]] = typer.Option(None, "--category", help="Categorias (ex: tecnologia economia)"),
    urls: Optional[List[str]] = typer.Option(None, "--url", "-u", help="Domínios permitidos (ex: g1.globo.com)"),
    limit: int = typer.Option(10, "--limit", "-n", help="Número máximo de resultados"),
    no_trends: bool = typer.Option(False, "--no-trends", help="Desabilitar Google Trends na pontuação"),
    output_json: bool = typer.Option(False, "--json", help="Saída em JSON"),
):
    """
    Recomenda artigos personalizados com base em keywords, localização e idioma.

    Exemplos:

        python cli.py recommend --keywords "IA" --country BR --language pt

        python cli.py recommend --keywords "economia" --keywords "dólar" --city "São Paulo"

        python cli.py recommend --category tecnologia --country BR --limit 20

        python cli.py recommend --keywords "futebol" --url globoesporte.com --url espn.com.br
    """
    _setup_db()

    # Expand keywords por vírgula (ex: --keywords "IA,ML,Python")
    expanded_kw: Optional[List[str]] = None
    if keywords:
        expanded_kw = []
        for kw in keywords:
            expanded_kw.extend([k.strip() for k in kw.split(",") if k.strip()])

    from app.schemas import RecommendationRequest
    from app.recommender.engine import recommend as _recommend

    req = RecommendationRequest(
        keywords=expanded_kw,
        countries=[c.upper() for c in countries] if countries else None,
        languages=[l.lower() for l in languages] if languages else None,
        cities=cities,
        categories=categories,
        urls=urls,
        limit=limit,
        use_trends=not no_trends,
    )

    console.print("[bold]Gerando recomendações...[/bold]")
    response = _run(_recommend(req))

    if output_json:
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return

    if response.trends_used:
        console.print(f"\n[cyan]Trends utilizados:[/cyan] {', '.join(response.trends_used[:5])}")

    _print_articles(response.articles, title="Artigos Recomendados")


# ---------------------------------------------------------------------------
# Comando: sources
# ---------------------------------------------------------------------------

@app.command()
def sources(
    country: Optional[str] = typer.Option(None, "--country", "-c"),
    language: Optional[str] = typer.Option(None, "--language", "-l"),
    category: Optional[str] = typer.Option(None, "--category"),
):
    """Lista os feeds RSS cadastrados no sistema."""
    from app.trends.rss_fetcher import get_sources_catalog
    catalog = get_sources_catalog(country=country, language=language, category=category)

    table = Table(title="Fontes RSS Cadastradas", box=box.ROUNDED)
    table.add_column("Nome", style="bold", min_width=20)
    table.add_column("País", width=5)
    table.add_column("Idioma", width=7)
    table.add_column("Categoria", width=14)
    table.add_column("URL", style="dim")

    for s in catalog:
        table.add_row(s.name, s.country, s.language, s.category, s.url)

    console.print(table)
    console.print(f"\n[dim]{len(catalog)} fontes encontradas[/dim]")


# ---------------------------------------------------------------------------
# Comando: serve
# ---------------------------------------------------------------------------

@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Endereço do servidor"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta do servidor"),
    reload: bool = typer.Option(False, "--reload", help="Hot reload para desenvolvimento"),
    workers: int = typer.Option(1, "--workers", "-w", help="Número de workers"),
):
    """Inicia o servidor da API REST."""
    import uvicorn
    console.print(f"[bold green]Iniciando API em http://{host}:{port}[/bold green]")
    console.print(f"[dim]Documentação: http://{host}:{port}/docs[/dim]")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level="info",
    )


if __name__ == "__main__":
    app()
