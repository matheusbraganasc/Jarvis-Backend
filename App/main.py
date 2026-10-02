from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from App.Core.ai_engine import JarvisBrain
from App.Core.config import settings

app = FastAPI(title="J.A.R.V.I.S. Central Server")
brain = JarvisBrain()

api_key_header = APIKeyHeader(name="X-API-Key")


def verificar_chave(chave: str = Security(api_key_header)):
    if not settings.JARVIS_SECRET_KEY or chave != settings.JARVIS_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Chave de API inválida.")
    return chave


class ChatRequest(BaseModel):
    message: str


class ResultadoFuncao(BaseModel):
    nome_funcao: str
    resultado: str


@app.get("/health")
def status_servidor():
    return {"status": "online", "sistema": "J.A.R.V.I.S. Backend operational"}


@app.post("/chat", dependencies=[Depends(verificar_chave)])
def processar_chat(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")
    return brain.processar_comando(payload.message)


@app.post("/chat/resultado-funcao", dependencies=[Depends(verificar_chave)])
def enviar_resultado_funcao(payload: ResultadoFuncao):
    return brain.continuar_apos_funcao(payload.nome_funcao, payload.resultado)