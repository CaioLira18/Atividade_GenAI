"""
tools.py
--------
Ferramentas disponíveis para o agente de e-commerce.

Cada ferramenta é decorada com @tool do LangChain, tornando-a disponível
para o modelo invocar automaticamente durante o loop agentic. O modelo
decide qual ferramenta usar com base na descrição de cada uma.

Ferramentas disponíveis:
    - executar_sql: Executa queries SELECT no banco SQLite e retorna tabela.
    - gerar_grafico: Executa SQL e salva um gráfico (bar/line/pie) como PNG.
    - listar_tabelas: Retorna o schema completo do banco de dados.

Segurança:
    - Apenas operações de leitura (SELECT / WITH) são permitidas.
    - Comandos de escrita (INSERT, UPDATE, DELETE, DROP, ALTER) são bloqueados.
    - Nomes de consumidores são anonimizados antes de exibir os resultados.
"""

import sqlite3
import os

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from langchain_core.tools import tool

matplotlib.use("Agg")  # Backend sem interface gráfica (compatível com servidores)

# Caminho do banco configurável via variável de ambiente
DB_PATH = os.getenv("DB_PATH", "banco.db")


# ──────────────────────────────────────────────────────────────────────────────
# Utilitários internos
# ──────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna uma nova conexão com o banco de dados SQLite."""
    return sqlite3.connect(DB_PATH)


def validar_query(query: str) -> str:
    """
    Verifica se a query contém comandos de escrita proibidos.

    Args:
        query (str): Query SQL a ser validada.

    Returns:
        str: A query original se válida, ou mensagem de erro se inválida.
    """
    comandos_proibidos = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER"]
    for comando in comandos_proibidos:
        if comando in query.upper():
            return f"❌ Operação não permitida: comando {comando} bloqueado."
    return query


def anonimizar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mascara dados pessoais identificáveis no DataFrame.

    Substitui nomes reais de consumidores por identificadores genéricos
    (ex: Cliente_0, Cliente_1) para proteger a privacidade dos dados.

    Args:
        df (pd.DataFrame): DataFrame com os resultados da query.

    Returns:
        pd.DataFrame: DataFrame com dados pessoais anonimizados.
    """
    if "nome_consumidor" in df.columns:
        df["nome_consumidor"] = "Cliente_" + df.index.astype(str)
    return df


def gerar_insight(df: pd.DataFrame) -> str:
    """
    Gera um insight automático com os valores máximo e mínimo da segunda coluna.

    Complementa a tabela de resultados com uma análise rápida dos extremos,
    facilitando a interpretação dos dados pelo usuário.

    Args:
        df (pd.DataFrame): DataFrame com os resultados da query.

    Returns:
        str: String formatada com o insight, ou string vazia em caso de erro.
    """
    try:
        if df.shape[1] >= 2:
            col = df.columns[1]
            max_val = df[col].max()
            min_val = df[col].min()
            return (
                f"\n\n**Insight:**\n"
                f"- Maior valor em `{col}`: **{max_val}**\n"
                f"- Menor valor em `{col}`: **{min_val}**"
            )
    except Exception:
        pass
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Ferramentas do agente
# ──────────────────────────────────────────────────────────────────────────────

@tool
def executar_sql(query: str) -> str:
    """
    Executa uma query SQL de leitura (SELECT) no banco de dados de e-commerce
    e retorna os resultados formatados como tabela Markdown.

    Use esta ferramenta para responder perguntas sobre vendas, produtos,
    consumidores, vendedores, entregas e avaliações. Resultados são limitados
    a 50 linhas para não sobrecarregar o contexto do modelo.

    Args:
        query (str): Query SQL SELECT válida para SQLite3.

    Returns:
        str: Tabela Markdown com os resultados e um insight automático,
             ou mensagem de erro em caso de falha.
    """
    query = query.strip().rstrip(";")

    # Guardrail: verifica se é uma operação de leitura
    comando = query.split()[0].upper()
    if comando not in ("SELECT", "WITH"):
        return "❌ Apenas queries de leitura (SELECT) são permitidas."

    # Guardrail: verifica comandos proibidos no corpo da query
    query_validada = validar_query(query)
    if query_validada.startswith("❌"):
        return query_validada

    try:
        conn = get_connection()
        df = pd.read_sql_query(query_validada, conn)
        conn.close()

        if df.empty:
            return "A consulta não retornou resultados."

        df = anonimizar(df)

        # Limita a exibição para não exceder o contexto do modelo
        if len(df) > 50:
            resultado = df.head(50).to_markdown(index=False)
            resultado += f"\n\n_(mostrando 50 de {len(df)} resultados)_"
        else:
            resultado = df.to_markdown(index=False)

        return resultado + gerar_insight(df)

    except Exception as e:
        return f"❌ Erro ao executar a query: {str(e)}"


@tool
def gerar_grafico(query: str, tipo: str, titulo: str, coluna_x: str, coluna_y: str) -> str:
    """
    Executa uma query SQL e gera um gráfico com os resultados, salvando-o
    como 'grafico.png' na pasta atual.

    Args:
        query (str): Query SQL SELECT a ser executada para obter os dados.
        tipo (str): Tipo do gráfico. Valores aceitos:
            - 'bar': Gráfico de barras verticais.
            - 'line': Gráfico de linha com marcadores.
            - 'pie': Gráfico de pizza com percentuais.
        titulo (str): Título exibido no topo do gráfico.
        coluna_x (str): Nome da coluna para o eixo X (ou rótulos no gráfico de pizza).
        coluna_y (str): Nome da coluna para o eixo Y (ou valores no gráfico de pizza).

    Returns:
        str: Mensagem de sucesso com o caminho do arquivo salvo,
             ou mensagem de erro em caso de falha.
    """
    query = query.strip().rstrip(";")

    if query.split()[0].upper() not in ("SELECT", "WITH"):
        return "❌ Apenas queries SELECT são permitidas para gráficos."

    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return "❌ A query não retornou dados para o gráfico."

        if coluna_x not in df.columns or coluna_y not in df.columns:
            colunas_disponiveis = list(df.columns)
            return (
                f"❌ Coluna '{coluna_x}' ou '{coluna_y}' não encontrada. "
                f"Colunas disponíveis: {colunas_disponiveis}"
            )

        fig, ax = plt.subplots(figsize=(10, 6))

        if tipo == "bar":
            ax.bar(df[coluna_x].astype(str), df[coluna_y], color="#4A90D9")
            plt.xticks(rotation=45, ha="right")
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)

        elif tipo == "line":
            ax.plot(df[coluna_x].astype(str), df[coluna_y], marker="o", color="#4A90D9")
            plt.xticks(rotation=45, ha="right")
            ax.set_xlabel(coluna_x)
            ax.set_ylabel(coluna_y)

        elif tipo == "pie":
            ax.pie(
                df[coluna_y],
                labels=df[coluna_x].astype(str),
                autopct="%1.1f%%",
                startangle=90,
            )
            ax.axis("equal")

        else:
            return f"❌ Tipo '{tipo}' inválido. Use: 'bar', 'line' ou 'pie'."

        ax.set_title(titulo)
        plt.tight_layout()

        output_path = "grafico.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        return f"✅ Gráfico '{titulo}' salvo em '{output_path}'."

    except Exception as e:
        return f"❌ Erro ao gerar gráfico: {str(e)}"


@tool
def listar_tabelas(dummy: str = "") -> str:
    """
    Retorna o schema completo do banco de dados: tabelas e suas colunas com tipos.

    Use esta ferramenta quando precisar verificar os nomes exatos de tabelas
    ou colunas antes de construir uma query SQL.

    Args:
        dummy (str): Parâmetro ignorado. Necessário pela interface do LangChain.

    Returns:
        str: Schema completo em formato Markdown, ou mensagem de erro.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        resultado = "**Tabelas disponíveis no banco de dados:**\n\n"
        for (table,) in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            col_list = ", ".join(f"`{c[1]}` ({c[2]})" for c in cols)
            resultado += f"**{table}**: {col_list}\n\n"

        conn.close()
        return resultado

    except Exception as e:
        return f"❌ Erro ao listar tabelas: {str(e)}"