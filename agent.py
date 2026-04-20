import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

from prompts import SYSTEM_PROMPT
from tools import executar_sql, gerar_grafico, listar_tabelas


# ──────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("❌ Variável GOOGLE_API_KEY não encontrada. Configure no .env")


# ──────────────────────────────────────────────
# Modelo + tools (NOVO PADRÃO)
# ──────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)

tools = [executar_sql, gerar_grafico, listar_tabelas]

# 🔥 Aqui está a mudança principal
llm_with_tools = llm.bind_tools(tools)


# ──────────────────────────────────────────────
# Prompt
# ──────────────────────────────────────────────

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])


# ──────────────────────────────────────────────
# Execução
# ──────────────────────────────────────────────

def run_agent(pergunta: str, chat_history: list):
    chain = prompt | llm_with_tools

    resposta = chain.invoke({
        "input": pergunta,
        "chat_history": chat_history,
    })

    # 🔥 Se o modelo quiser usar uma tool
    if hasattr(resposta, "tool_calls") and resposta.tool_calls:
        for tool_call in resposta.tool_calls:
            nome = tool_call["name"]
            args = tool_call["args"]

            # Executa a tool correta
            for tool in tools:
                if tool.name == nome:
                    resultado_tool = tool.invoke(args)

                    # adiciona no histórico como resposta da tool
                    chat_history.append(resposta)
                    chat_history.append(
                        AIMessage(content=str(resultado_tool))
                    )

                    return str(resultado_tool), chat_history

    # Caso não use tool
    chat_history.append(HumanMessage(content=pergunta))
    chat_history.append(resposta)

    return resposta.content, chat_history


# ──────────────────────────────────────────────
# Loop
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