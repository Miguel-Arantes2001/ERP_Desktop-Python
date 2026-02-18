from urllib import response
import requests
from services.api import API_URL, clear_token, get_headers,set_token,api_request
import os


def login(email: str, password: str):
    response = requests.post(
        f"{API_URL}/login",
        data={
            "username": email,
            "password": password
        }
    )

    if response.status_code == 200:
        set_token(response.json()["access_token"])
        return True, None

    return False, response.json().get("detail", "Erro no login")

def get_me():
   
    headers = get_headers()

    if not headers:
        return None

    response = api_request("GET", f"{API_URL}/me", headers=headers)

    if not response:
        return None
    
    return response