# 🛒 Agente de Análise de E-Commerce — Rocket Lab 2026

Agente conversacional de **Text-to-SQL** desenvolvido com **LangChain** e **Gemini 2.5 Flash** que permite a usuários não técnicos realizarem consultas e análises sobre dados de um sistema de e-commerce em linguagem natural.

> Projeto desenvolvido para a atividade de GenAI do programa **Visagio Rocket Lab 2026**.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Demonstração](#demonstração)
- [Tecnologias](#tecnologias)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Base de Dados](#base-de-dados)
- [Como Executar](#como-executar)
- [Exemplos de Perguntas](#exemplos-de-perguntas)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)

---

## Visão Geral

O agente recebe perguntas em português, gera automaticamente queries SQL, executa no banco de dados SQLite e retorna respostas formatadas com insights — tudo sem que o usuário precise saber SQL.

Áreas de análise suportadas:

- **Vendas e Receita** — produtos mais vendidos, receita por categoria, ticket médio
- **Logística e Entrega** — status de pedidos, pontualidade por estado, atrasos
- **Satisfação** — avaliações por vendedor, categorias com maior taxa negativa
- **Consumidores** — volume por estado, perfil de compra
- **Vendedores e Produtos** — ranking de performance, produtos por região

---

## Demonstração

```
Você: Quais são os 10 produtos mais vendidos?

Agente: | nome_produto         | total_vendas |
        |----------------------|--------------|
        | Produto A            | 527          |
        | Produto B            | 489          |
        | ...                  | ...          |

        Insight: O produto mais vendido teve 527 unidades,
        enquanto o 10º colocado teve 201 — uma diferença de 2.6x.
```

---

## Tecnologias

| Tecnologia | Versão | Uso |
|---|---|---|
| Python | 3.12+ | Linguagem principal |
| LangChain | ≥ 0.2.0 | Framework de agentes |
| Gemini 2.5 Flash | — | Modelo de linguagem (Text-to-SQL) |
| SQLite3 | embutido | Banco de dados |
| Streamlit | — | Interface visual |
| Pandas | ≥ 2.0 | Manipulação de dados |
| Matplotlib | ≥ 3.8 | Geração de gráficos |
| FastAPI | — | API REST (integração com frontend) |

---

## Estrutura do Projeto

```
Atividade_GenAI/
│
├── agent.py          # Lógica principal do agente (loop de tool calls)
├── api.py            # API REST com FastAPI para integração com frontend
├── app.py            # Interface Streamlit (modo standalone)
├── tools.py          # Ferramentas do agente: SQL, gráficos, schema
├── prompts.py        # System prompt com schema e instruções do agente
│
├── banco.db          # Banco de dados SQLite com dados do e-commerce
├── requirements.txt  # Dependências Python
├── .env              # Variáveis de ambiente (não versionar)
├── .env.example      # Modelo de configuração do .env
└── README.md
```

---

## Base de Dados

Banco SQLite (`banco.db`) com **7 tabelas** e mais de **500 mil registros**:

| Tabela | Registros | Descrição |
|---|---|---|
| `dim_consumidores` | 99.441 | Cadastro de consumidores |
| `dim_produtos` | 32.951 | Catálogo de produtos e categorias |
| `dim_vendedores` | 3.095 | Cadastro de vendedores |
| `fat_pedidos` | 99.441 | Dados de entrega e logística |
| `fat_pedido_total` | 99.441 | Valores financeiros dos pedidos |
| `fat_itens_pedidos` | 112.650 | Itens individuais por pedido |
| `fat_avaliacoes_pedidos` | 95.307 | Avaliações e comentários |

### Diagrama de Relacionamento

```
dim_consumidores ──────┐
                        ├──── fat_pedidos ────── fat_avaliacoes_pedidos
dim_produtos ──────┐   │
                    ├── fat_itens_pedidos
dim_vendedores ────┘   │
                        └──── fat_pedido_total
```

---

## Como Executar

### Pré-requisitos

- Python **3.12** ou superior
- Chave de API do Google Gemini → [Obter em Google AI Studio](https://aistudio.google.com/app/apikey)
- Arquivo `banco.db` na raiz do projeto

### Passo a Passo

**1. Clone o repositório**
```bash
git clone https://github.com/seu-usuario/Atividade_GenAI.git
cd Atividade_GenAI
```

**2. Crie o ambiente virtual**
```bash
python -m venv venv
```

**3. Ative o ambiente virtual**
```bash
# Windows
.\venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

**4. Instale as dependências**
```bash
pip install -r requirements.txt
```

**5. Crie e Ative o Venv e coloque a chave do gemini 'GOOGLE_API_KEY= Sua Chave'**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**6. Configure as variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto:
```env
GOOGLE_API_KEY=sua_chave_aqui
DB_PATH=banco.db
```

> ⚠️ Nunca versione o arquivo `.env`. Ele já está no `.gitignore`.

**6. Execute a aplicação**

```bash
# Interface Streamlit (recomendado)
streamlit run app.py

# Ou via terminal (modo CLI)
python agent.py

# Ou via API REST
uvicorn api:app --reload --port 8001
```

A interface Streamlit abrirá automaticamente em `http://localhost:8501`.

---

## Exemplos de Perguntas

```
# Vendas e Receita
"Quais são os 10 produtos mais vendidos?"
"Qual a receita total por categoria de produto?"
"Qual o ticket médio dos pedidos por estado?"

# Logística
"Qual o percentual de pedidos entregues no prazo por estado?"
"Quais estados têm maior atraso médio nas entregas?"
"Quantos pedidos existem por status?"

# Avaliações
"Qual a média de avaliação geral dos pedidos?"
"Quais os 10 vendedores com melhor avaliação média?"
"Quais categorias têm maior taxa de avaliação negativa?"

# Consumidores
"Quais estados têm maior volume de pedidos?"
"Quais estados têm maior ticket médio?"

# Gráficos
"Gere um gráfico de barras com os 10 estados com mais pedidos"
"Mostre um gráfico de pizza da receita por categoria"
```

---

## Funcionalidades

### ✅ Implementadas

- **Text-to-SQL** — conversão automática de linguagem natural para SQL
- **Histórico de conversa** — memória entre perguntas na mesma sessão
- **Geração de gráficos** — bar, line e pie charts salvos como PNG
- **Anonimização** — nomes de consumidores são mascarados nas respostas
- **Guardrails** — apenas queries SELECT/WITH são permitidas (sem escrita no banco)
- **Cache de respostas** — perguntas repetidas retornam instantaneamente
- **Insights automáticos** — max/min destacados ao final das tabelas
- **Interface Streamlit** — chat visual com histórico
- **API REST (FastAPI)** — endpoint `/perguntar` para integração com frontend
- **Sessões por usuário** — histórico isolado por `session_id` na API

### 🛠️ Ferramentas do Agente

| Ferramenta | Descrição |
|---|---|
| `executar_sql` | Executa SELECT no banco e retorna tabela formatada em markdown |
| `gerar_grafico` | Executa SQL e salva gráfico (bar/line/pie) como `grafico.png` |
| `listar_tabelas` | Retorna schema completo do banco para o modelo consultar |

---

## Arquitetura

```
┌─────────────────────────────────────────────┐
│              Interfaces de Entrada           │
│   Streamlit (app.py) │ CLI │ API (api.py)   │
└─────────────────┬───────────────────────────┘
                  │ pergunta (texto)
                  ▼
┌─────────────────────────────────────────────┐
│                  agent.py                   │
│  • Monta prompt com histórico               │
│  • Chama Gemini 2.5 Flash via LangChain     │
│  • Loop de execução de ferramentas          │
│  • Cache de respostas                       │
└──────┬──────────────────────────────────────┘
       │ tool calls
       ▼
┌─────────────────────────────────────────────┐
│                  tools.py                   │
│  executar_sql │ gerar_grafico │ listar_tabelas│
└──────┬──────────────────────────────────────┘
       │ SQL
       ▼
┌─────────────────────────────────────────────┐
│               banco.db (SQLite)             │
│         7 tabelas · +500k registros         │
└─────────────────────────────────────────────┘
```