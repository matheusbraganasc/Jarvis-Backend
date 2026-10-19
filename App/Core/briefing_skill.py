from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
import requests
from App.Core.google_services import (
    buscar_emails_nao_lidos,
    buscar_tarefas_pendentes,
)

# Feeds RSS de Tecnologia e Jogos
RSS_FEEDS = {
    "tecnologia": "https://olhardigital.com.br/feed/",
    "jogos": "https://br.ign.com/feed.xml",
}


def buscar_noticias_rss(limite_por_categoria: int = 2) -> list:
    """Busca as últimas notícias de tecnologia e jogos via RSS."""
    noticias = []

    for categoria, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limite_por_categoria]:
                # Extrai a imagem de capa da notícia
                imagem = None
                if "media_content" in entry and len(entry["media_content"]) > 0:
                    imagem = entry["media_content"][0].get("url")
                elif "links" in entry:
                    for link in entry["links"]:
                        if link.get("type", "").startswith("image/"):
                            imagem = link.get("href")
                            break

                noticias.append(
                    {
                        "titulo": entry.title,
                        "categoria": categoria,
                        "fonte": (
                            "Olhar Digital"
                            if categoria == "tecnologia"
                            else "IGN Brasil"
                        ),
                        "link": entry.link,
                        "data": entry.get("published", ""),
                        "imagem": (
                            imagem
                            or "https://via.placeholder.com/600x340?text=J.A.R.V.I.S.+News"
                        ),
                    }
                )
        except Exception as e:
            print(f"[RSS LOG] Erro ao buscar feed {categoria}: {e}")

    return noticias


def gerar_morning_briefing() -> dict:
    """Gera o relatório estruturado do Briefing Matinal com prioridade dinâmica:

    1. Avalia E-mails -> 2. Tarefas -> 3. Notícias.
    Retorna o payload JSON para alimentar os Pop-ups da Opção A no HUD.
    """
    fuso_ceara = ZoneInfo("America/Fortaleza")
    agora = datetime.now(fuso_ceara)

    meses_pt = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro",
    }

    data_formatada = f"{agora.day} de {meses_pt[agora.month]} de {agora.year}"
    hora_atual = agora.strftime("%H:%M")

    # Clima em tempo real (Fortaleza / Caucaia)
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-3.7172&longitude=-38.5433&current_weather=true"
        res = requests.get(url, timeout=4).json()
        temp = res["current_weather"]["temperature"]
        clima_txt = f"fazendo {temp} graus Celsius na região metropolitana"
    except Exception:
        clima_txt = "com dados meteorológicos indisponíveis no momento"

    # Consultas reais às APIs da Google e RSS
    emails = buscar_emails_nao_lidos()
    tarefas = buscar_tarefas_pendentes()
    noticias = buscar_noticias_rss()

    # --- LÓGICA DE PRIORIDADE E NARRAÇÃO POR VOZ ---
    texto_fala = f"Bom dia, Senhor. Hoje é {data_formatada}, exatamente {hora_atual}. O clima está {clima_txt}. "

    # 1. Prioridade E-mails
    if len(emails) > 0:
        texto_fala += f"Constam {len(emails)} e-mails importantes não lidos na sua caixa de entrada. "
    else:
        texto_fala += "Sua caixa de entrada está limpa e sem e-mails pendentes. "

    # 2. Prioridade Tarefas
    if len(tarefas) > 0:
        texto_fala += (
            f"Para o dia de hoje, você possui {len(tarefas)} tarefas agendadas. "
        )
    else:
        texto_fala += "Não há compromissos nem tarefas pendentes no seu cronograma de hoje. "

    # 3. Prioridade Notícias
    if len(noticias) > 0:
        texto_fala += f"Em destaque nas notícias: {noticias[0]['titulo']}. "

    texto_fala += "Relatório concluído e sistemas em alerta."

    # Retorno estruturado para o HUD
    return {
        "tipo": "briefing_popup",
        "skill": "MORNING_BRIEFING",
        "resposta": texto_fala,
        "dados": {"emails": emails, "tarefas": tarefas, "noticias": noticias},
    }
