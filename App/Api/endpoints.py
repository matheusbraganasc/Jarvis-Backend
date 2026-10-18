from datetime import datetime
import requests
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from App.Core.ai_engine import JarvisBrain

router = APIRouter()

# Instancia o cérebro do Jarvis
brain = JarvisBrain()

class ChatRequest(BaseModel):
    message: str

def executar_skill_local(directive: str):
    """Executa tarefas locais instantâneas sem gastar quota da IA."""
    directive_upper = directive.upper()
    
    # 1. SKILL: CLIMA EM TEMPO REAL (Fortaleza / Caucaia)
    if any(k in directive_upper for k in ["CLIMA", "TEMPO", "CHOVER", "TEMPERATURA"]):
        try:
            # Consulta aberta e gratuita de meteorologia para a região de Fortaleza/Caucaia
            url = "https://api.open-meteo.com/v1/forecast?latitude=-3.7172&longitude=-38.5433&current_weather=true"
            res = requests.get(url, timeout=5).json()
            temp = res["current_weather"]["temperature"]
            
            resposta = f"Senhor, a temperatura atual na região é de {temp} graus Celsius, com condições estáveis."
            return {"tipo": "texto", "skill": "METEO_SKILL", "resposta": resposta}
        except Exception:
            return {"tipo": "texto", "skill": "METEO_SKILL", "resposta": "Senhor, os sensores meteorológicos externos estão temporariamente inacessíveis."}

    # 2. SKILL: BRIEFING MATINAL (Relatório Completo)
    elif any(k in directive_upper for k in ["BOM DIA", "BRIEFING", "RELATÓRIO MATINAL", "RESUMO DO DIA"]):
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        data_atual = agora.strftime("%d de %B de %Y")
        
        try:
            url = "https://api.open-meteo.com/v1/forecast?latitude=-3.7172&longitude=-38.5433&current_weather=true"
            res = requests.get(url, timeout=4).json()
            temp = res["current_weather"]["temperature"]
            clima_txt = f"fazendo {temp} graus"
        except:
            clima_txt = "com dados meteorológicos indisponíveis no momento"

        resposta = (
            f"Bom dia, Senhor. Sistemas operacionais totalmente online. "
            f"Hoje é {data_atual}, exatamente {hora_atual}. "
            f"Na região metropolitana, o clima encontra-se {clima_txt}. "
            f"Os núcleos centrais estão estáveis e prontos para as diretrizes de desenvolvimento de hoje."
        )
        return {"tipo": "texto", "skill": "MORNING_BRIEFING", "resposta": resposta}

    return None

@router.post("/chat")
async def chat_endpoint(payload: ChatRequest, x_api_key: str = Header(None)):
    mensagem = payload.message.strip()
    if not mensagem:
        raise HTTPException(status_code=400, detail="Mensagem vazia.")

    # 1. Tenta executar uma Skill Local primeiro (Responde de imediato e economiza a API)
    resultado_skill = executar_skill_local(mensagem)
    if resultado_skill:
        # Adiciona ao histórico do cérebro para manter o contexto das conversas
        brain.historico.append({"role": "user", "content": mensagem})
        brain.historico.append({"role": "model", "content": resultado_skill["resposta"]})
        return resultado_skill

    # 2. Se não for skill local, processa via cérebro inteligente (Gemini / Groq / Ferramentas)
    resposta_ia = brain.processar_comando(mensagem)
    return resposta_ia
