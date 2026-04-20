import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from prompts import SYSTEM_PROMPT
from tools import executar_sql, gerar_grafico, listar_tabelas


# ──────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY não encontrada")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)

tools = [executar_sql, gerar_grafico, listar_tabelas]
llm_with_tools = llm.bind_tools(tools)

# Mapa de nome → função para execução das tools
tools_map = {t.name: t for t in tools}

# ──────────────────────────────────────────────
# Prompt
# ──────────────────────────────────────────────

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])


# ──────────────────────────────────────────────
# Execução com loop de tool calls
# ──────────────────────────────────────────────

cache = {}

def run_agent(pergunta: str, chat_history: list):
    if pergunta in cache:
        return cache[pergunta], chat_history

    # Monta as mensagens completas (histórico + pergunta atual)
    mensagens = []
    # Adiciona system + histórico via prompt template
    formatted = prompt.format_messages(
        input=pergunta,
        chat_history=chat_history,
    )

    try:
        resposta = llm_with_tools.invoke(formatted)
    except Exception as e:
        if "429" in str(e):
            return "Limite da API atingido. Tente novamente em alguns segundos.", chat_history
        raise e

    # Loop: enquanto o modelo quiser usar ferramentas, executamos e devolvemos o resultado
    max_iter = 10
    iteracao = 0

    while resposta.tool_calls and iteracao < max_iter:
        iteracao += 1

        # Adiciona a resposta do modelo (com tool_calls) ao histórico de mensagens
        formatted.append(resposta)

        # Executa cada tool call e coleta os resultados
        for tc in resposta.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id   = tc["id"]

            if tool_name in tools_map:
                tool_result = tools_map[tool_name].invoke(tool_args)
            else:
                tool_result = f"❌ Ferramenta '{tool_name}' não encontrada."

            formatted.append(
                ToolMessage(content=str(tool_result), tool_call_id=tool_id)
            )

        # Chama o modelo novamente com os resultados das ferramentas
        try:
            resposta = llm_with_tools.invoke(formatted)
        except Exception as e:
            if "429" in str(e):
                return "Limite da API atingido. Tente novamente em alguns segundos.", chat_history
            raise e

    # Extrai o texto final
    if isinstance(resposta.content, list):
        # Gemini pode retornar lista de partes
        resultado = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in resposta.content
        ).strip()
    else:
        resultado = resposta.content or "Sem resposta."

    cache[pergunta] = resultado

    chat_history.append(HumanMessage(content=pergunta))
    chat_history.append(AIMessage(content=resultado))

    return resultado, chat_history


# ──────────────────────────────────────────────
# Loop CLI
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  🛒  Agente de Análise de E-Commerce  ")
    print("  Powered by Gemini + LangChain (LCEL)")
    print("=" * 60)

    chat_history = []

    while True:
        try:
            pergunta = input("\nVocê: ").strip()
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

        print(f"{'─'*60}")
        print(f"Agente: {resposta}")
        print(f"{'─'*60}")


if __name__ == "__main__":
    main()