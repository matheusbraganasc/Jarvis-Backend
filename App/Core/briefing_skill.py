from datetime import datetime
from zoneinfo import ZoneInfo
import feedparser
import requests
from App.Core.google_services import (
    buscar_emails_nao_lidos,
    buscar_tarefas_pendentes,
)

# Feeds RSS
RSS_FEEDS = {
    "tecnologia": "https://olhardigital.com.br/feed/",
    "corinthians": "https://ge.globo.com/rss/ge/futebol/times/corinthians/",
}


def buscar_noticias_rss() -> list:
    """Busca notícias de Tecnologia e do Corinthians."""
    noticias = []
    for categoria, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:  # Pegamos as 2 principais de cada
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
                        "fonte": "GE Corinthians"
                        if categoria == "corinthians"
                        else "Olhar Digital",
                        "link": entry.link,
                        "imagem": (
                            imagem
                            or "https://via.placeholder.com/600x340?text=J.A.R.V.I.S.+News"
                        ),
                    }
                )
        except Exception as e:
            print(f"[RSS LOG] Erro ao buscar {categoria}: {e}")
    return noticias


def gerar_morning_briefing() -> dict:
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

    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-3.7172&longitude=-38.5433&current_weather=true"
        res = requests.get(url, timeout=4).json()
        temp = res["current_weather"]["temperature"]
        clima_txt = f"fazendo {temp} graus Celsius na região metropolitana"
    except Exception:
        clima_txt = "com clima ameno na região"

    emails = buscar_emails_nao_lidos()
    tarefas = buscar_tarefas_pendentes()
    noticias = buscar_noticias_rss()

    # Verifica se há e-mail da Unifametro
    emails_unifametro = [
        e
        for e in emails
        if "unifametro" in e["remetente"].lower()
        or "unifametro" in e["assunto"].lower()
    ]

    # Estruturação por Passos da Animação
    passos = []

    # 1. Introdução
    fala_intro = f"Bom dia, Senhor. Hoje é {data_formatada}, exatamente {hora_atual}. O clima está {clima_txt}."
    passos.append({"tipo": "intro", "fala": fala_intro, "dados": None})

    # 2. E-mails
    if len(emails) > 0:
        if len(emails_unifametro) > 0:
            fala_email = f"Atenção, Senhor. O senhor recebeu {len(emails)} novos e-mails, com destaque importante para uma mensagem da Unifametro."
        else:
            fala_email = f"Na sua caixa de entrada, consta um total de {len(emails)} novos e-mails não lidos."
    else:
        fala_email = "Sua caixa de entrada está limpa. O senhor não tem nenhum e-mail pendente hoje."
    passos.append({"tipo": "emails", "fala": fala_email, "dados": emails})

    # 3. Tarefas
    if len(tarefas) > 0:
        fala_tarefas = f"Sobre as suas tarefas: você possui {len(tarefas)} compromissos agendados para hoje. Fique atento."
    else:
        fala_tarefas = (
            "Hoje o senhor não tem nenhuma tarefa ou compromisso pendente."
        )
    passos.append({"tipo": "tarefas", "fala": fala_tarefas, "dados": tarefas})

    # 4. Notícias
    if len(noticias) > 0:
        passos.append({
            "tipo": "noticias_intro",
            "fala": "As notícias do dia estão interessantes, Senhor.",
            "dados": None,
        })
        for item in noticias[:3]:  # Fala sobre até 3 notícias
            fala_noticia = (
                f"Em destaque no {item['fonte']}: {item['titulo']}."
            )
            passos.append(
                {"tipo": "noticia_item", "fala": fala_noticia, "dados": item}
            )
    else:
        passos.append({
            "tipo": "noticias_intro",
            "fala": "Hoje o mundo está calmo e sem notícias relevantes, Senhor.",
            "dados": None,
        })

    # 5. Encerramento
    passos.append({
        "tipo": "outro",
        "fala": "Esse é o nosso resumo de hoje. Qualquer coisa, estarei à sua inteira disposição.",
        "dados": None,
    })

    return {
        "tipo": "briefing_sequencial",
        "skill": "MORNING_BRIEFING",
        "passos": passos,
    }


# --- COMANDOS INDIVIDUAIS SEPARADOS ---


def buscar_somente_emails() -> dict:
    emails = buscar_emails_nao_lidos()
    emails_unifametro = [
        e
        for e in emails
        if "unifametro" in e["remetente"].lower()
        or "unifametro" in e["assunto"].lower()
    ]
    if len(emails) > 0:
        fala = f"O senhor possui {len(emails)} e-mails não lidos."
        if len(emails_unifametro) > 0:
            fala += " Incluindo mensagens importantes da Unifametro."
    else:
        fala = "Não há e-mails não lidos na sua caixa de entrada, Senhor."

    return {
        "tipo": "single_popup",
        "categoria": "emails",
        "fala": fala,
        "dados": emails,
    }


def buscar_somente_tarefas() -> dict:
    tarefas = buscar_tarefas_pendentes()
    if len(tarefas) > 0:
        fala = f"O senhor possui {len(tarefas)} tarefas pendentes para hoje."
    else:
        fala = "Nenhuma tarefa agendada no seu Google Tasks para hoje, Senhor."

    return {
        "tipo": "single_popup",
        "categoria": "tarefas",
        "fala": fala,
        "dados": tarefas,
    }


def buscar_somente_noticias() -> dict:
    noticias = buscar_noticias_rss()
    if len(noticias) > 0:
        fala = f"Aqui estão as principais notícias de hoje, com destaque para: {noticias[0]['titulo']}."
    else:
        fala = "Não consegui obter atualizações de notícias no momento, Senhor."

    return {
        "tipo": "single_popup",
        "categoria": "noticias",
        "fala": fala,
        "dados": noticias,
    }
