from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from App.Core.ai_engine import JarvisBrain
from App.Core.briefing_skill import gerar_morning_briefing
from App.Core.config import settings

app = FastAPI(title="J.A.R.V.I.S. Central Server")

# --- CONFIGURAÇÃO DE CORS (LIBERA O HUD WEB) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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


def executar_skill_local(directive: str):
    """Executa tarefas locais instantâneas sem gastar quota da IA."""
    directive_upper = directive.upper()

    # 1. SKILL: CLIMA EM TEMPO REAL (Fortaleza / Caucaia)
    if any(k in directive_upper for k in ["CLIMA", "TEMPO", "CHOVER", "TEMPERATURA"]):
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=-3.7172&longitude=-38.5433&current_weather=true"
            res = requests.get(url, timeout=5).json()
            temp = res["current_weather"]["temperature"]

            resposta = f"Senhor, a temperatura atual na região é de {temp} graus Celsius, com condições estáveis."
            return {"tipo": "texto", "skill": "METEO_SKILL", "resposta": resposta}
        except Exception:
            return {
                "tipo": "texto",
                "skill": "METEO_SKILL",
                "resposta": "Senhor, os sensores meteorológicos externos estão temporariamente inacessíveis.",
            }

    # 2. SKILL: BRIEFING MATINAL (Relatório Completo com RSS e Dados Estruturados)
    elif any(
        k in directive_upper
        for k in ["BOM DIA", "BRIEFING", "RELATÓRIO MATINAL", "RESUMO DO DIA"]
    ):
        return gerar_morning_briefing()

    return None


@app.get("/")
def read_root():
    """Rota raiz para manter o serviço ativo e responder ao health check do Render"""
    return {"status": "online", "system": "J.A.R.V.I.S. Backend operational"}


@app.get("/health")
def status_servidor():
    return {"status": "online", "sistema": "J.A.R.V.I.S. Backend operational"}


@app.post("/chat")
def processar_chat(payload: ChatRequest, api_key: str = Security(validar_api_key)):
    mensagem = payload.message.strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    # 1. Tenta executar a Skill Local primeiro (Instantânea e com dados estruturados)
    resultado_skill = executar_skill_local(mensagem)
    if resultado_skill:
        brain.historico.append({"role": "user", "content": mensagem})
        brain.historico.append(
            {"role": "model", "content": resultado_skill["resposta"]}
        )
        return resultado_skill

    # 2. Se não for skill local, processa via cérebro de IA (Gemini/Groq)
    resposta = brain.processar_comando(mensagem)
    return resposta


@app.post("/chat/resultado-funcao")
def processar_resultado_funcao(
    payload: ResultadoFuncao, api_key: str = Security(validar_api_key)
):
    resposta = brain.continuar_apos_funcao(payload.nome_funcao, payload.resultado)
    return resposta
