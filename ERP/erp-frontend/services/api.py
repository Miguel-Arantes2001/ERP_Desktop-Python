import os
import requests
from PySide6.QtWidgets import QMessageBox

API_URL = "http://127.0.0.1:8000"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(BASE_DIR, "token.txt")

def set_token(new_token: str):
    with open(TOKEN_PATH, "w",encoding='utf-8') as f:
        f.write(new_token)

def get_token():
    if not os.path.exists(TOKEN_PATH):
        return None

    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        token = f.read().strip()

    return token or None


def clear_token():
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)


def get_headers():
    token = get_token()
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }


def api_request(method:str, url, **kwargs):
    headers = get_headers()
    kwargs["headers"] = headers

    try:
        response = requests.request(method, url, **kwargs)
    except requests.exceptions.RequestException :
        QMessageBox.critical(None, "Erro", "Falha de conexão com o servidor")
        return None
    
    if response.status_code == 401:
        clear_token()
        QMessageBox.warning(
            None,
            "Sessão expirada",
            "Sua sessão expirou.\nPor favor, faça login novamente."
        )
        return None 

    if not response.ok:
        QMessageBox.warning(
            None,
            "Erro",
            f"Erro {response.status_code}: {response.text}"
        )
        return None

    if response.content:
        return response.json()

    return None