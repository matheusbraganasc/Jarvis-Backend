import base64
import edge_tts


async def gerar_audio_jarvis_b64(texto: str) -> str:
    """Gera o áudio usando a voz AntonioNeural da Microsoft e devolve em Base64."""
    VOICE = "pt-BR-AntonioNeural"

    # Limpa caracteres táticos para não serem lidos
    texto_limpo = (
        texto.replace("//", "")
        .replace("[", "")
        .replace("]", "")
        .replace("*", "")
        .replace("#", "")
        .strip()
    )

    if not texto_limpo:
        return ""

    # Ajuste para postura mais grave e cadenciada
    communicate = edge_tts.Communicate(
        texto_limpo, VOICE, rate="-5%", pitch="-4Hz"
    )

    audio_bytes = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])

    # Converte para string Base64 pronta para o elemento Audio do React/HTML
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:audio/mp3;base64,{audio_b64}"
