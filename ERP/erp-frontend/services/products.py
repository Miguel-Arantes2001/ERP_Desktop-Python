from urllib import response

from services.api import API_URL, get_headers,api_request

def list_products():
    response =api_request("GET", f"{API_URL}/products")
    return  response or []

def create_product(data):
    response = api_request("POST", f"{API_URL}/products", json=data)
    return response is not None

def add_stock(product_id: int, quantity: int, reason: str = ""):
     return api_request(
        "POST",
        f"{API_URL}/products/{product_id}/add-stock",
        json={"quantity": quantity, "reason": reason}
    ) is not None