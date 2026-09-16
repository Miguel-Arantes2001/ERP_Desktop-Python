from urllib import response

from services.api import API_URL, get_headers,api_request

def list_products():
    return api_request("GET", f"{API_URL}/products")

def create_product(data):
    return api_request("POST", f"{API_URL}/products", json=data)

def add_stock(product_id: int, quantity: float, reason: str = ""):
     return api_request(
        "POST",
        f"{API_URL}/products/{product_id}/add-stock",
        json={"quantity": quantity, "reason": reason}
    ) is not None


def update_product_barcode(product_id: int, barcode: str):
    return api_request(
        "PATCH",
        f"{API_URL}/products/{product_id}/barcode",
        json={"barcode": barcode}
    )


def update_product(product_id: int, data: dict):
    return api_request(
        "PATCH",
        f"{API_URL}/products/{product_id}",
        json=data
    )


def search_products(name: str):
    response = api_request("GET", f"{API_URL}/products", params={"search": name})
    
    return response or []

def get_product_by_barcode(barcode: str):
    response = api_request("GET", f"{API_URL}/products/barcode/{barcode}")
    
    return response


def get_product(product_id: int):
    return api_request("GET", f"{API_URL}/products/{product_id}")


def create_photo_session(product_id: int):
    return api_request(
        "POST",
        f"{API_URL}/products/{product_id}/photo-session",
    )


def rotate_product_photo(product_id: int):
    return api_request(
        "POST",
        f"{API_URL}/products/{product_id}/rotate-photo",
    )