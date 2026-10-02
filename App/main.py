from fastapi import FastAPI, HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from App.Core.ai_engine import JarvisBrain
from App.Core.config import settings

app = FastAPI(title="J.A.R.V.I.S. Central Server")
brain = JarvisBrain()

# Configuração de Segurança por API Key
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def validar_api_key(x_api_key: str = Security(api_key_header)):
    if x_api_key != settings.JARVIS_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return x_api_key

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

class ResultadoFuncao(BaseModel):
    nome_funcao: str
    resultado: str

@app.get("/")
def read_root():
    """Rota raiz para manter o serviço ativo e responder ao health check do Render"""
    return {"status": "online", "system": "J.A.R.V.I.S. Backend operational"}

@app.get("/health")
def status_servidor():
    return {"status": "online", "sistema": "J.A.R.V.I.S. Backend operational"}

@app.post("/chat")
def processar_chat(payload: ChatRequest, api_key: str = Security(validar_api_key)):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")
    
    resposta = brain.processar_comando(payload.message)
    return resposta

@app.post("/chat/resultado-funcao")
def processar_resultado_funcao(payload: ResultadoFuncao, api_key: str = Security(validar_api_key)):
    resposta = brain.continuar_apos_funcao(payload.nome_funcao, payload.resultado)
    return resposta
