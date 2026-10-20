from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from App.Core.ai_engine import JarvisBrain
from App.Core.briefing_skill import (
    gerar_morning_briefing,
    buscar_somente_emails,
    buscar_somente_tarefas,
    buscar_somente_noticias,
)
from App.Core.config import settings
from App.Core.tts_service import gerar_audio_jarvis_b64

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

    # 2. SKILL: BRIEFING MATINAL COMPLETO (Relatório Sequencial Animado)
    elif any(
        k in directive_upper
        for k in ["BOM DIA", "BRIEFING", "RELATÓRIO MATINAL", "RESUMO DO DIA"]
    ):
        return gerar_morning_briefing()

    # 3. COMANDO ISOLADO: E-MAILS
    elif any(k in directive_upper for k in ["E-MAIL", "EMAIL", "EMAILS", "CAIXA DE ENTRADA", "MENSAGENS"]):
        res = buscar_somente_emails()
        return {
            "tipo": "single_popup",
            "categoria": "emails",
            "skill": "EMAIL_SKILL",
            "resposta": res["fala"],
            "dados": res["dados"],
        }

    # 4. COMANDO ISOLADO: TAREFAS
    elif any(k in directive_upper for k in ["TAREFA", "TAREFAS", "AGENDA", "COMPROMISSO", "COMPROMISSOS"]):
        res = buscar_somente_tarefas()
        return {
            "tipo": "single_popup",
            "categoria": "tarefas",
            "skill": "TASKS_SKILL",
            "resposta": res["fala"],
            "dados": res["dados"],
        }

    # 5. COMANDO ISOLADO: NOTÍCIAS / CORINTHIANS
    elif any(k in directive_upper for k in ["NOTÍCIA", "NOTICIA", "NOTÍCIAS", "NOTICIAS", "CORINTHIANS", "FEEDS"]):
        res = buscar_somente_noticias()
        return {
            "tipo": "single_popup",
            "categoria": "noticias",
            "skill": "NEWS_SKILL",
            "resposta": res["fala"],
            "dados": res["dados"],
        }

    return None


@app.get("/")
def read_root():
    """Rota raiz para manter o serviço ativo e responder ao health check do Render"""
    return {"status": "online", "system": "J.A.R.V.I.S. Backend operational"}


@app.get("/health")
def status_servidor():
    return {"status": "online", "sistema": "J.A.R.V.I.S. Backend operational"}


@app.post("/chat")
async def processar_chat(payload: ChatRequest, api_key: str = Security(validar_api_key)):
    mensagem = payload.message.strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    # 1. Tenta executar a Skill Local primeiro (Instantânea e com dados estruturados)
    resultado_skill = executar_skill_local(mensagem)
    if resultado_skill:
        # Se for briefing sequencial, gera o áudio Base64 para cada passo individual
        if resultado_skill.get("tipo") == "briefing_sequencial" and "passos" in resultado_skill:
            for passo in resultado_skill["passos"]:
                if passo.get("fala"):
                    passo["audio_b64"] = await gerar_audio_jarvis_b64(passo["fala"])
            fala_historico = resultado_skill["passos"][0]["fala"]
        else:
            fala_historico = resultado_skill.get("resposta", "Executando skill...")
            if fala_historico:
                resultado_skill["audio_b64"] = await gerar_audio_jarvis_b64(fala_historico)

        brain.historico.append({"role": "user", "content": mensagem})
        brain.historico.append({"role": "model", "content": fala_historico})
        return resultado_skill

    # 2. Se não for skill local, processa via cérebro de IA (Gemini/Groq)
    resposta = brain.processar_comando(mensagem)
    
    # Extrai a string de resposta se a IA retornar um dicionário ou objeto
    texto_resposta = resposta.get("resposta", str(resposta)) if isinstance(resposta, dict) else str(resposta)
    audio_b64 = await gerar_audio_jarvis_b64(texto_resposta)

    if isinstance(resposta, dict):
        resposta["audio_b64"] = audio_b64
        return resposta

    return {
        "resposta": resposta,
        "audio_b64": audio_b64,
        "tipo": "texto",
        "skill": "BRAIN_MODULE"
    }


@app.post("/chat/resultado-funcao")
async def processar_resultado_funcao(
    payload: ResultadoFuncao, api_key: str = Security(validar_api_key)
):
    resposta = brain.continuar_apos_funcao(payload.nome_funcao, payload.resultado)
    texto_resposta = resposta.get("resposta", str(resposta)) if isinstance(resposta, dict) else str(resposta)
    audio_b64 = await gerar_audio_jarvis_b64(texto_resposta)

    if isinstance(resposta, dict):
        resposta["audio_b64"] = audio_b64
        return resposta

    return {"resposta": resposta, "audio_b64": audio_b64}
