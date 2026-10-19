import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/tasks.readonly',
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token.json')


def obter_credenciais():
    """Carrega credenciais da variável de ambiente (Render), do token.json local ou executa autorização CLI simples."""
    creds = None

    # 1. Tenta carregar da variável de ambiente (Render)
    env_token = os.getenv("GOOGLE_TOKEN_JSON")
    if env_token:
        try:
            token_data = json.loads(env_token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"[GOOGLE API LOG] Erro ao ler GOOGLE_TOKEN_JSON da ENV: {e}")

    # 2. Tenta carregar do ficheiro token.json local (se existir)
    if not creds and os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"[GOOGLE API LOG] Erro ao ler token.json: {e}")

    # 3. Renova o token se estiver expirado
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[GOOGLE API LOG] Erro ao renovar token: {e}")
            creds = None

    # 4. Se ainda não houver credenciais (geração do token no Termux)
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_PATH):
            print(
                "[GOOGLE API LOG] Ficheiro credentials.json não encontrado em App/Core/"
            )
            return None

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH, SCOPES, redirect_uri="urn:ietf:wg:oauth:2.0:oob"
        )

        auth_url, _ = flow.authorization_url(prompt="consent")

        print("\n" + "=" * 60)
        print("INSTRUÇÕES DE AUTENTICAÇÃO GOOGLE (TERMUX):")
        print("1. Copie o URL abaixo e cole no Chrome do seu celular.")
        print("2. Faça login, autorize o J.A.R.V.I.S. e copie o código gerado.")
        print("=" * 60 + "\n")
        print(f"URL: {auth_url}\n")

        code = input("Cole o código de autorização do Google aqui: ").strip()

        flow.fetch_token(code=code)
        creds = flow.credentials

        # Salva o token.json localmente
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
            print("\n[SUCESSO] token.json gerado na pasta App/Core/\n")

    return creds


def buscar_emails_nao_lidos(limite: int = 5) -> list:
    """Busca os últimos e-mails não lidos da Caixa de Entrada principal (ignorando spam)."""
    try:
        creds = obter_credenciais()
        if not creds:
            return []

        service = build("gmail", "v1", credentials=creds)
        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread category:primary", maxResults=limite)
            .execute()
        )

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            headers = msg_data.get("payload", {}).get("headers", [])

            remetente = "Desconhecido"
            assunto = "Sem Assunto"
            data_envio = ""

            for header in headers:
                if header["name"].lower() == "from":
                    remetente = (
                        header["value"]
                        .split("<")[0]
                        .strip()
                        .replace('"', "")
                    )
                elif header["name"].lower() == "subject":
                    assunto = header["value"]
                elif header["name"].lower() == "date":
                    data_envio = header["value"]

            emails.append(
                {"remetente": remetente, "assunto": assunto, "data": data_envio}
            )

        return emails
    except Exception as e:
        print(f"[GMAIL API LOG] Erro ao buscar e-mails: {e}")
        return []


def buscar_tarefas_pendentes(limite: int = 5) -> list:
    """Busca as tarefas pendentes do Google Tasks."""
    try:
        creds = obter_credenciais()
        if not creds:
            return []

        service = build("tasks", "v1", credentials=creds)
        results = (
            service.tasks()
            .list(tasklist="@default", showCompleted=False, maxResults=limite)
            .execute()
        )
        items = results.get("items", [])

        tarefas = []
        for item in items:
            tarefas.append({
                "titulo": item.get("title", "Tarefa sem título"),
                "detalhes": item.get("notes", ""),
                "vencimento": item.get("due", ""),
            })

        return tarefas
    except Exception as e:
        print(f"[TASKS API LOG] Erro ao buscar tarefas: {e}")
        return []
