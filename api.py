from fastapi import FastAPI
from agent import run_agent

app = FastAPI()
history = []

@app.get("/perguntar")
def perguntar(q: str):
    global history
    resposta, history = run_agent(q, history)
    return {"resposta": resposta}