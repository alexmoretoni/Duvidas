from __future__ import annotations

from fastapi import APIRouter

from app.recommender.engine import recommend
from app.schemas import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommend", tags=["Recomendação"])


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Recomendação personalizada de artigos",
    description="""
Recomenda artigos com base nos parâmetros fornecidos:

- **keywords**: palavras-chave de interesse
- **urls**: filtrar por domínios/fontes (ex: `["g1.globo.com", "folha.uol.com.br"]`)
- **categories**: categorias de conteúdo (ex: `["tecnologia", "economia"]`)
- **cities**: filtrar por menção de cidades (ex: `["São Paulo", "Rio de Janeiro"]`)
- **countries**: filtrar por países ISO 3166-1 (ex: `["BR", "PT"]`)
- **languages**: filtrar por idiomas ISO 639-1 (ex: `["pt", "en"]`)
- **limit**: número máximo de artigos retornados (1-100)
- **use_trends**: incorporar Google Trends na pontuação (padrão: true)

Os artigos são pontuados por relevância considerando:
keywords do usuário, trends do Google, frescor do artigo, autoridade da fonte e relevância geográfica.
""",
)
async def get_recommendations(req: RecommendationRequest) -> RecommendationResponse:
    return await recommend(req)
