
import os
import json
import requests  
from PySide6.QtWidgets import QMessageBox

API_URL = "http://127.0.0.1:8000"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOKENS_PATH = os.path.join(BASE_DIR, "tokens.json")


def _read_tokens() -> dict:
    if not os.path.exists(TOKENS_PATH):
        return {}

    try:
        with open(TOKENS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_tokens(tokens: dict):
    with open(TOKENS_PATH, "w", encoding="utf-8") as f:
        json.dump(tokens, f)


def set_tokens(access_token: str, refresh_token: str):
    _write_tokens({
        "access_token": access_token,
        "refresh_token": refresh_token,
    })


def set_token(new_access_token: str):
    tokens = _read_tokens()
    tokens["access_token"] = new_access_token
    _write_tokens(tokens)


def get_token():
    return _read_tokens().get("access_token")


def get_refresh_token():
    return _read_tokens().get("refresh_token")


def clear_token():
    if os.path.exists(TOKENS_PATH):
        os.remove(TOKENS_PATH)


def get_headers():
    token = get_token()
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}"
    }


def _try_refresh_access_token() -> bool:
    refresh_token = get_refresh_token()
    if not refresh_token:
        return False

    try:
        response = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return False

    if response.status_code != 200:
        return False

    set_token(response.json()["access_token"])
    return True


def api_request(method: str, url, _retry_after_refresh: bool = True, **kwargs):
    headers = get_headers()
    kwargs["headers"] = headers

    try:
        response = requests.request(method, url, **kwargs)
    except requests.exceptions.RequestException:
        QMessageBox.critical(None, "Erro", "Falha de conexão com o servidor")
        return None

    if response.status_code == 401:
    
        if _retry_after_refresh and _try_refresh_access_token():
            return api_request(method, url, _retry_after_refresh=False, **kwargs)
            
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