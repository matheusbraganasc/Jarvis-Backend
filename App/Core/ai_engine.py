import os
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

class JarvisBrain:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        self.system_instruction = (
            "Você é o J.A.R.V.I.S., assistente pessoal do Senhor. "
            "Responda sempre em português, de forma objetiva, eficiente e refinada. "
            "Suas respostas serão lidas por síntese de voz; evite emojis, tabelas ou formatações Markdown complexas."
        )

    def _chamar_gemini(self, texto: str) -> str:
        client = genai.Client(api_key=self.gemini_key)
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config={"system_instruction": self.system_instruction}
        )
        resposta = chat.send_message(texto)
        return resposta.text

    def _chamar_groq(self, texto: str) -> str:
        client = Groq(api_key=self.groq_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": self.system_instruction},
                {"role": "user", "content": texto}
            ]
        )
        return completion.choices[0].message.content

    def processar_comando(self, texto: str) -> str:
        # 1. Tenta Gemini (Provedor Principal)
        if self.gemini_key:
            try:
                return self._chamar_gemini(texto)
            except Exception as e:
                print(f"[AVISO]: Gemini indisponível ({e}). Alternando para Groq...")

        # 2. Backup: Groq / Llama 3.3
        if self.groq_key:
            try:
                return self._chamar_groq(texto)
            except Exception as e:
                print(f"[ERRO]: Groq falhou ({e}).")

        return "Perdão, Senhor. Todos os nós de processamento de IA estão indisponíveis no momento."
