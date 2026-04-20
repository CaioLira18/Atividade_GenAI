import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
from langchain_core.tools import tool

DB_PATH = os.getenv("DB_PATH", "banco.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


@tool
def executar_sql(query: str) -> str:
    """
    Executa uma query SQL de leitura (SELECT) no banco de dados de e-commerce.
    Retorna os resultados como texto formatado em tabela.
    Use esta ferramenta para responder perguntas sobre vendas, produtos,
    consumidores, vendedores, entregas e avaliações.
    """
    query = query.strip().rstrip(";")

    # Guardrail: apenas leitura
    comando = query.split()[0].upper()
    if comando not in ("SELECT", "WITH"):
        return "❌ Apenas queries de leitura (SELECT) são permitidas."

    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return "A consulta não retornou resultados."

        # Limita exibição a 50 linhas para não sobrecarregar o contexto
        if len(df) > 50:
            resultado = df.head(50).to_markdown(index=False)
            resultado += f"\n\n_(mostrando 50 de {len(df)} resultados)_"
        else:
            resultado = df.to_markdown(index=False)

        return resultado

    except Exception as e:
        return f"❌ Erro ao executar a query: {str(e)}"


@tool
def gerar_grafico(query: str, tipo: str, titulo: str, coluna_x: str, coluna_y: str) -> str:
    """
    Executa uma query SQL e gera um gráfico com os resultados.
    Salva o gráfico como 'grafico.png' na pasta atual.

    Parâmetros:
    - query: SQL SELECT a ser executado
    - tipo: tipo do gráfico — 'bar' (barras), 'line' (linha) ou 'pie' (pizza)
    - titulo: título do gráfico
    - coluna_x: nome da coluna para o eixo X (ou rótulos no caso de pizza)
    - coluna_y: nome da coluna para o eixo Y (ou valores no caso de pizza)
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
            return f"❌ Colunas '{coluna_x}' ou '{coluna_y}' não encontradas. Colunas disponíveis: {list(df.columns)}"

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
            return f"❌ Tipo de gráfico '{tipo}' inválido. Use: bar, line ou pie."

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
    Lista todas as tabelas disponíveis no banco de dados e suas colunas.
    Use esta ferramenta caso precise consultar o schema do banco.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        resultado = "**Tabelas disponíveis:**\n\n"
        for (table,) in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            col_list = ", ".join(f"{c[1]} ({c[2]})" for c in cols)
            resultado += f"**{table}**: {col_list}\n\n"

        conn.close()
        return resultado

    except Exception as e:
        return f"❌ Erro ao listar tabelas: {str(e)}"