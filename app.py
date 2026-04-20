import streamlit as st
from agent import run_agent

st.set_page_config(page_title="Agente de E-commerce", page_icon="🛒")
st.title("Agente de E-commerce")

# Inicializa histórico e mensagens exibidas
if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibe o histórico de mensagens
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input de chat (aparece na parte inferior, como um chat moderno)
pergunta = st.chat_input("Faça sua pergunta sobre o e-commerce...")

if pergunta:
    # Mostra a mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Processa e mostra a resposta
    with st.chat_message("assistant"):
        with st.spinner("Analisando..."):
            resposta, st.session_state.history = run_agent(
                pergunta, st.session_state.history
            )
        st.markdown(resposta)

    st.session_state.messages.append({"role": "assistant", "content": resposta})