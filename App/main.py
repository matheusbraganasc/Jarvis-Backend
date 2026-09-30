from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from App.Core.ai_engine import JarvisBrain

app = FastAPI(title="J.A.R.V.I.S. Central Server")
brain = JarvisBrain()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/health")
def status_servidor():
    return {"status": "online", "sistema": "J.A.R.V.I.S. Backend operational"}

@app.post("/chat", response_model=ChatResponse)
def processar_chat(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")
    
    resposta = brain.processar_comando(payload.message)
    return ChatResponse(response=resposta)
