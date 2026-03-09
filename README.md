# Trending Article Recommender

Sistema que analisa **trends e tópicos em alta** e recomenda artigos através de palavras-chave, URLs, ideias, cidades, países e idiomas.

## Fontes de dados (sem API key necessária)

| Fonte | Tipo | Cobertura |
|---|---|---|
| Google Trends | Trending topics | 13+ países |
| Google News RSS | Artigos por país/idioma/query | 10+ locales |
| 30+ feeds RSS públicos | Artigos | BR, PT, US, GB, DE, FR, ES, AR |

**Fontes brasileiras incluídas:** G1, Folha, Estadão, UOL, Agência Brasil, BBC Brasil, El País Brasil, Tecmundo, Canaltech, TechTudo, Exame, InfoMoney, Valor Econômico, Deutsche Welle PT.

## Instalação

```bash
# Clone e entre no diretório
cd Duvidas

# Instale as dependências
pip install -r requirements.txt

# Copie as configurações
cp .env.example .env
```

## Configuração (`.env`)

```env
DEFAULT_LANGUAGE=pt        # idioma padrão
DEFAULT_COUNTRY=BR         # país padrão
CACHE_TTL=3600             # cache em segundos (1 hora)
TRENDS_SLEEP=60            # intervalo entre chamadas ao Google Trends
MAX_ARTICLES=100           # máximo de artigos por busca
DB_PATH=./cache.db         # caminho do banco SQLite
```

## CLI

### Ver trends em alta

```bash
# Brasil (padrão)
python cli.py trends

# Outros países
python cli.py trends --country US --language en
python cli.py trends --country PT --language pt
python cli.py trends --country ES --language es

# Saída JSON
python cli.py trends --json
```

### Buscar artigos

```bash
# Busca simples
python cli.py search "inteligência artificial"

# Com filtros
python cli.py search "economia" --country BR --language pt --limit 20

# Filtrar por fonte
python cli.py search "tecnologia" --source tecmundo
```

### Recomendações personalizadas

```bash
# Por keyword e país
python cli.py recommend --keywords "IA" --country BR

# Múltiplas keywords
python cli.py recommend --keywords "IA,machine learning,python" --country BR --language pt

# Filtro por cidade
python cli.py recommend --keywords "imóveis" --city "São Paulo" --city "Rio de Janeiro"

# Filtro por categoria
python cli.py recommend --category tecnologia --country BR --limit 20

# Filtro por domínio/fonte
python cli.py recommend --keywords "futebol" --url globoesporte.com --url espn.com.br

# Múltiplos países/idiomas
python cli.py recommend --keywords "economy" --country US --country GB --language en

# Sem Google Trends (apenas keywords do usuário)
python cli.py recommend --keywords "política" --no-trends

# Saída em JSON para integração
python cli.py recommend --keywords "IA" --country BR --json
```

### Listar fontes RSS

```bash
# Todas as fontes
python cli.py sources

# Por país
python cli.py sources --country BR

# Por categoria
python cli.py sources --category tecnologia
```

### Iniciar servidor API

```bash
# Produção
python cli.py serve

# Desenvolvimento (hot reload)
python cli.py serve --reload --port 8000

# Porta customizada
python cli.py serve --host 0.0.0.0 --port 9000
```

## API REST

Após `python cli.py serve`, acesse:

- **Documentação interativa:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints principais

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/trends` | Trending topics por país/idioma |
| `GET` | `/trends/keywords` | Apenas as keywords trending |
| `GET` | `/trends/countries` | Países suportados |
| `GET` | `/articles/search?q=...` | Busca artigos por query |
| `GET` | `/articles/cached` | Artigos em cache local |
| `GET` | `/articles/sources/list` | Catálogo de feeds RSS |
| `POST` | `/recommend` | Recomendação personalizada |
| `GET` | `/health` | Status da API |

### Exemplos de uso da API

```bash
# Trending topics do Brasil
curl "http://localhost:8000/trends?country=BR&language=pt"

# Keywords em alta
curl "http://localhost:8000/trends/keywords?country=BR"

# Buscar artigos
curl "http://localhost:8000/articles/search?q=inteligencia+artificial&country=BR&language=pt"

# Recomendação completa
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["inteligência artificial", "tecnologia"],
    "countries": ["BR"],
    "languages": ["pt"],
    "categories": ["tecnologia"],
    "limit": 10,
    "use_trends": true
  }'

# Filtrar por cidade e domínio
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["imóveis", "mercado imobiliário"],
    "cities": ["São Paulo", "Rio de Janeiro"],
    "urls": ["g1.globo.com", "folha.uol.com.br"],
    "languages": ["pt"],
    "limit": 15
  }'
```

## Algoritmo de Pontuação

Cada artigo recebe um score de 0 a 1 baseado em 5 fatores ponderados:

| Fator | Peso | Descrição |
|---|---|---|
| Keyword match | 35% | Match das keywords do usuário no título/texto/tags |
| Trend boost | 25% | Menciona keywords em alta do Google Trends |
| Frescor | 20% | Artigos recentes recebem maior pontuação (meia-vida: 24h) |
| Autoridade da fonte | 10% | Fontes reconhecidas (G1, BBC, Reuters, etc.) |
| Relevância geográfica | 10% | Match de país/cidade nos filtros |

## Arquitetura

```
cli.py                  ← Interface CLI (Typer)
app/
├── main.py             ← FastAPI app
├── config.py           ← Configurações (.env)
├── database.py         ← SQLite / aiosqlite
├── schemas.py          ← Modelos Pydantic
├── crud.py             ← Cache de artigos e trends
├── trends/
│   ├── google_trends.py ← pytrends (Google Trends)
│   └── rss_fetcher.py   ← feedparser + 30+ RSS feeds
├── recommender/
│   ├── filters.py       ← Filtros por idioma/país/cidade/keyword/domínio
│   ├── scorer.py        ← Algoritmo de pontuação multi-fator
│   └── engine.py        ← Pipeline de recomendação
└── routers/
    ├── trends.py        ← /trends
    ├── articles.py      ← /articles
    └── recommend.py     ← /recommend
```

## Países e Idiomas Suportados

| País | Código | Idioma |
|---|---|---|
| Brasil | BR | pt |
| Portugal | PT | pt |
| Estados Unidos | US | en |
| Reino Unido | GB | en |
| Alemanha | DE | de |
| França | FR | fr |
| Espanha | ES | es |
| Argentina | AR | es |
| México | MX | es |
| Colômbia | CO | es |
| Japão | JP | ja |
| Austrália | AU | en |
| Índia | IN | en |

## Notas sobre Rate Limiting

- **Google Trends:** O Google pode limitar requisições excessivas. O sistema usa cache SQLite (padrão: 1 hora) para minimizar chamadas. Configure `TRENDS_SLEEP=60` para aguardar entre requisições.
- **Google News RSS:** Sem limite oficial. O sistema faz requisições normais de RSS.
- **Feeds RSS públicos:** Cada fonte tem seus próprios limites. O sistema trata falhas graciosamente.
