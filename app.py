"""
app.py
------
Interface visual do agente de e-commerce construída com Streamlit.

Disponibiliza um chat interativo no navegador onde o usuário pode fazer
perguntas em linguagem natural e receber respostas com tabelas e insights
diretamente do agente. O histórico da conversa é mantido durante a sessão.

Uso:
    streamlit run app.py

A aplicação abrirá automaticamente em http://localhost:8501.
"""

import streamlit as st
from agent import run_agent

# ──────────────────────────────────────────────────────────────────────────────
# Configuração da página
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Agente de E-commerce",
    page_icon="🛒",
    layout="centered",
)

st.title("🛒 Agente de E-commerce")
st.caption("Faça perguntas em português sobre vendas, produtos, entregas e avaliações.")

# ──────────────────────────────────────────────────────────────────────────────
# Estado da sessão
# ──────────────────────────────────────────────────────────────────────────────

# `history`: lista de mensagens LangChain usada internamente pelo agente
if "history" not in st.session_state:
    st.session_state.history = []

# `messages`: lista de dicts {role, content} para renderização no chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# ──────────────────────────────────────────────────────────────────────────────
# Renderização do histórico de mensagens
# ──────────────────────────────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ──────────────────────────────────────────────────────────────────────────────
# Input do usuário
# ──────────────────────────────────────────────────────────────────────────────

pergunta = st.chat_input("Ex: Quais são os 10 produtos mais vendidos?")

if pergunta:
    # Exibe a mensagem do usuário imediatamente
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Processa a pergunta e exibe a resposta do agente
    with st.chat_message("assistant"):
        with st.spinner("Analisando dados..."):
            resposta, st.session_state.history = run_agent(
                pergunta,
                st.session_state.history,
            )
        st.markdown(resposta)

    st.session_state.messages.append({"role": "assistant", "content": resposta})