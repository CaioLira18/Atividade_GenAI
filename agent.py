"""
agent.py
--------
Módulo principal do agente de análise de e-commerce.

Implementa um agente conversacional baseado em LangChain (LCEL) que utiliza
o modelo Gemini 2.5 Flash para converter perguntas em linguagem natural em
queries SQL, executá-las no banco de dados e retornar respostas formatadas.

Fluxo de execução:
    1. A pergunta do usuário é formatada junto ao histórico de conversa.
    2. O modelo é invocado e pode decidir chamar ferramentas (tool calls).
    3. As ferramentas são executadas e os resultados devolvidos ao modelo.
    4. O loop se repete até o modelo produzir uma resposta textual final.
    5. A resposta e o histórico atualizado são retornados ao chamador.
"""

import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from prompts import SYSTEM_PROMPT
from tools import executar_sql, gerar_grafico, listar_tabelas


# ──────────────────────────────────────────────────────────────────────────────
# Configuração do modelo
# ──────────────────────────────────────────────────────────────────────────────

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError(
        "❌ GOOGLE_API_KEY não encontrada. "
        "Configure a variável no arquivo .env antes de iniciar."
    )

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,  # Respostas determinísticas para análise de dados
)

# Ferramentas disponíveis para o agente
tools = [executar_sql, gerar_grafico, listar_tabelas]
llm_with_tools = llm.bind_tools(tools)

# Mapeamento nome → função para despacho dinâmico durante o loop de tool calls
tools_map = {t.name: t for t in tools}


# ──────────────────────────────────────────────────────────────────────────────
# Template de prompt
# ──────────────────────────────────────────────────────────────────────────────

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])


# ──────────────────────────────────────────────────────────────────────────────
# Cache em memória
# ──────────────────────────────────────────────────────────────────────────────

# Evita reprocessar perguntas idênticas na mesma sessão de processo.
# Para ambientes multi-worker (ex: Uvicorn com workers), considere Redis.
cache: dict[str, str] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Função principal do agente
# ──────────────────────────────────────────────────────────────────────────────

def run_agent(pergunta: str, chat_history: list) -> tuple[str, list]:
    """
    Executa o agente com uma pergunta e retorna a resposta e o histórico atualizado.

    O agente opera em um loop agentic: enquanto o modelo solicitar o uso de
    ferramentas, elas são executadas e os resultados devolvidos ao modelo.
    O loop encerra quando o modelo produz uma resposta textual final ou ao
    atingir o limite de iterações.

    Args:
        pergunta (str): Pergunta em linguagem natural do usuário.
        chat_history (list): Histórico de mensagens da conversa atual.
            Deve conter objetos HumanMessage e AIMessage do LangChain.

    Returns:
        tuple[str, list]: Tupla contendo:
            - str: Resposta textual final do agente.
            - list: Histórico atualizado com a nova pergunta e resposta.

    Raises:
        Exception: Propaga exceções não relacionadas a rate limit da API.
    """
    # Verifica cache antes de invocar o modelo
    if pergunta in cache:
        return cache[pergunta], chat_history

    # Formata as mensagens com sistema + histórico + pergunta atual
    formatted = prompt.format_messages(
        input=pergunta,
        chat_history=chat_history,
    )

    # Primeira invocação do modelo
    try:
        resposta = llm_with_tools.invoke(formatted)
    except Exception as e:
        if "429" in str(e):
            return "⚠️ Limite da API atingido. Aguarde alguns segundos e tente novamente.", chat_history
        raise

    # ── Loop agentic de tool calls ─────────────────────────────────────────
    MAX_ITERACOES = 10
    iteracao = 0

    while resposta.tool_calls and iteracao < MAX_ITERACOES:
        iteracao += 1

        # Inclui a resposta do modelo (com tool_calls) no contexto
        formatted.append(resposta)

        # Executa cada ferramenta solicitada e coleta os resultados
        for tc in resposta.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            if tool_name in tools_map:
                tool_result = tools_map[tool_name].invoke(tool_args)
            else:
                tool_result = f"❌ Ferramenta '{tool_name}' não encontrada."

            formatted.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_id)
            )

        # Nova invocação com os resultados das ferramentas no contexto
        try:
            resposta = llm_with_tools.invoke(formatted)
        except Exception as e:
            if "429" in str(e):
                return "⚠️ Limite da API atingido. Aguarde alguns segundos e tente novamente.", chat_history
            raise

    # ── Extração do texto final ────────────────────────────────────────────
    # O Gemini pode retornar o conteúdo como string ou como lista de partes
    if isinstance(resposta.content, list):
        resultado = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in resposta.content
        ).strip()
    else:
        resultado = resposta.content or "Sem resposta."

    # Armazena no cache e atualiza o histórico
    cache[pergunta] = resultado
    chat_history.append(HumanMessage(content=pergunta))
    chat_history.append(AIMessage(content=resultado))

    return resultado, chat_history


# ──────────────────────────────────────────────────────────────────────────────
# Interface de linha de comando (CLI)
# ──────────────────────────────────────────────────────────────────────────────

def main():
    """Inicia o loop interativo de chat no terminal."""
    print("=" * 60)
    print("  🛒  Agente de Análise de E-Commerce")
    print("  Powered by Gemini 2.5 Flash + LangChain")
    print("=" * 60)
    print("Digite sua pergunta em português. ('sair' para encerrar)\n")

    chat_history = []

    while True:
        try:
            pergunta = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not pergunta:
            continue

        if pergunta.lower() in ("sair", "exit", "quit"):
            print("Até logo! 👋")
            break

        print("\nAgente: pensando...\n")
        resposta, chat_history = run_agent(pergunta, chat_history)
        print(f"{'─' * 60}")
        print(f"Agente: {resposta}")
        print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()