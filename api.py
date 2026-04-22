"""
api.py
------
API REST do agente de e-commerce construída com FastAPI.

Expõe endpoints para integração do agente com frontends externos (ex: React),
gerenciando sessões de conversa independentes por usuário via session_id.

Endpoints:
    POST /agente/perguntar  — Envia uma pergunta ao agente.
    DELETE /agente/sessao/{session_id} — Limpa o histórico de uma sessão.
    GET  /agente/health     — Verifica se o serviço está online.

Uso:
    uvicorn api:app --reload --port 8001

Integração com o backend do e-commerce:
    Inclua o router deste módulo no main.py do backend principal:

        from api import router as agente_router
        app.include_router(agente_router)
"""

from fastapi import APIRouter
from pydantic import BaseModel

from agent import run_agent

router = APIRouter(prefix="/agente", tags=["Agente IA"])

# Armazenamento em memória de históricos por sessão.
# Cada chave é um session_id; o valor é a lista de mensagens LangChain.
# Para produção com múltiplos workers, substitua por Redis ou banco externo.
sessions: dict[str, list] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Schemas de entrada e saída
# ──────────────────────────────────────────────────────────────────────────────

class PerguntaRequest(BaseModel):
    """Payload de entrada para o endpoint de chat."""
    pergunta: str
    session_id: str = "default"


class PerguntaResponse(BaseModel):
    """Payload de saída do endpoint de chat."""
    resposta: str
    session_id: str


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/perguntar", response_model=PerguntaResponse)
def perguntar(body: PerguntaRequest):
    """
    Recebe uma pergunta em linguagem natural e retorna a resposta do agente.

    O histórico da conversa é mantido por sessão, permitindo perguntas
    de acompanhamento (ex: "e o segundo colocado?") com contexto preservado.

    Args:
        body (PerguntaRequest): Objeto com `pergunta` e `session_id`.

    Returns:
        PerguntaResponse: Objeto com `resposta` e `session_id`.
    """
    session_id = body.session_id

    # Inicializa histórico para sessões novas
    if session_id not in sessions:
        sessions[session_id] = []

    resposta, sessions[session_id] = run_agent(body.pergunta, sessions[session_id])

    return PerguntaResponse(resposta=resposta, session_id=session_id)


@router.delete("/sessao/{session_id}")
def limpar_sessao(session_id: str):
    """
    Remove o histórico de conversa de uma sessão específica.

    Útil para reiniciar o contexto sem encerrar a aplicação,
    como ao clicar em "Nova conversa" no frontend.

    Args:
        session_id (str): Identificador da sessão a ser limpa.

    Returns:
        dict: Confirmação da operação com o session_id afetado.
    """
    if session_id in sessions:
        del sessions[session_id]
    return {"ok": True, "session_id": session_id}


@router.get("/health")
def health():
    """
    Verifica se o serviço do agente está operacional.

    Returns:
        dict: Status do serviço.
    """
    return {"status": "ok", "agente": "online"}