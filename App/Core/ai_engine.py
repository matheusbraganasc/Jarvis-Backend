import json
from typing import Any

from google import genai
from google.genai import types
from groq import Groq
from App.Core.config import settings

SYSTEM_INSTRUCTION = (
    "Você é o J.A.R.V.I.S., assistente pessoal do Senhor. "
    "Responda sempre em português, de forma breve, eficiente e refinada. "
    "Suas respostas serão lidas por voz, evite caracteres especiais ou emojis."
)

FERRAMENTAS_SCHEMA_GEMINI = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="checar_bateria",
            description="Verifica a porcentagem da bateria do celular.",
        ),
        types.FunctionDeclaration(
            name="controlar_lanterna",
            description="Liga ou desliga a lanterna do celular.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "estado": types.Schema(type="STRING", enum=["on", "off"]),
                },
                required=["estado"],
            ),
        ),
        types.FunctionDeclaration(
            name="abrir_aplicativo",
            description="Abre um aplicativo ou site no celular.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "nome_app": types.Schema(type="STRING"),
                },
                required=["nome_app"],
            ),
        ),
    ])
]

FERRAMENTAS_SCHEMA_GROQ = [
    {
        "type": "function",
        "function": {
            "name": "checar_bateria",
            "description": "Verifica a porcentagem da bateria do celular.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_lanterna",
            "description": "Liga ou desliga a lanterna do celular.",
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {"type": "string", "enum": ["on", "off"]},
                },
                "required": ["estado"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_aplicativo",
            "description": "Abre um aplicativo ou site no celular.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_app": {"type": "string"},
                },
                "required": ["nome_app"],
            },
        },
    },
]


class JarvisBrain:
    def __init__(self):
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

        self.groq_client = None
        if settings.GROQ_API_KEY:
            self.groq_client = Groq(api_key=settings.GROQ_API_KEY)

        self.historico = []

    def _montar_contents_gemini(self):
        contents = []
        for item in self.historico:
            role = item["role"]
            if role == "function":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part(text=item["content"])],
                    )
                )
            else:
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=item["content"])],
                    )
                )
        return contents

    def _montar_mensagens_groq(self):
        mensagens = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for item in self.historico:
            role = "assistant" if item["role"] == "model" else "user"
            mensagens.append({"role": role, "content": item["content"]})
        return mensagens

    def _chamar_gemini(self, incluir_tools: bool):
        if not self.gemini_client:
            raise RuntimeError("Cliente Gemini não configurado.")

        config_kwargs: dict[str, Any] = dict(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        )
        if incluir_tools:
            config_kwargs["tools"] = FERRAMENTAS_SCHEMA_GEMINI
            config_kwargs["automatic_function_calling"] = (
                types.AutomaticFunctionCallingConfig(disable=True)
            )

        return self.gemini_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=self._montar_contents_gemini(),
            config=types.GenerateContentConfig(**config_kwargs),
        )

    def _chamar_groq(self, incluir_tools: bool):
        if not self.groq_client:
            raise RuntimeError("Cliente Groq não configurado.")

        kwargs: dict[str, Any] = dict(
            messages=self._montar_mensagens_groq(),
            model="openai/gpt-oss-120b",
        )
        if incluir_tools:
            kwargs["tools"] = FERRAMENTAS_SCHEMA_GROQ

        return self.groq_client.chat.completions.create(**kwargs)

    def processar_comando(self, mensagem: str) -> dict:
        self.historico.append({"role": "user", "content": mensagem})

        if self.gemini_client:
            try:
                response = self._chamar_gemini(incluir_tools=True)
                parte = response.candidates[0].content.parts[0]

                if parte.function_call:
                    return {
                        "tipo": "function_call",
                        "nome": parte.function_call.name,
                        "argumentos": dict(parte.function_call.args),
                    }

                texto = response.text
                self.historico.append({"role": "model", "content": texto})
                return {"tipo": "texto", "resposta": texto}

            except Exception as e:
                print(f"[AI ENGINE LOG] Falha no Gemini: {e}")

        if self.groq_client:
            try:
                response = self._chamar_groq(incluir_tools=True)
                mensagem_resposta = response.choices[0].message

                if mensagem_resposta.tool_calls:
                    chamada = mensagem_resposta.tool_calls[0]
                    return {
                        "tipo": "function_call",
                        "nome": chamada.function.name,
                        "argumentos": json.loads(chamada.function.arguments),
                    }

                texto = mensagem_resposta.content
                self.historico.append({"role": "model", "content": texto})
                return {"tipo": "texto", "resposta": texto}

            except Exception as e:
                print(f"[AI ENGINE LOG] Falha no Groq: {e}")

        return {
            "tipo": "texto",
            "resposta": "Perdão, Senhor. Todos os nós de processamento de IA estão indisponíveis no momento.",
        }

    def continuar_apos_funcao(self, nome_funcao: str, resultado_execucao: str) -> dict:
        self.historico.append({
            "role": "function",
            "content": f"Resultado de {nome_funcao}: {resultado_execucao}",
        })

        if self.gemini_client:
            try:
                response = self._chamar_gemini(incluir_tools=False)
                texto = response.text
                self.historico.append({"role": "model", "content": texto})
                return {"tipo": "texto", "resposta": texto}
            except Exception as e:
                print(f"[AI ENGINE LOG] Falha no Gemini: {e}")

        if self.groq_client:
            try:
                response = self._chamar_groq(incluir_tools=False)
                texto = response.choices[0].message.content
                self.historico.append({"role": "model", "content": texto})
                return {"tipo": "texto", "resposta": texto}
            except Exception as e:
                print(f"[AI ENGINE LOG] Falha no Groq: {e}")

        return {
            "tipo": "texto",
            "resposta": "Perdão, Senhor. Não consegui concluir o processamento do resultado.",
        }