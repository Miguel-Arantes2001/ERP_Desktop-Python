from typing import Any, Dict
from services.api import API_URL, get_headers,api_request


def get_product_by_barcode(barcode: str):
    response = api_request("GET", f"{API_URL}/products/barcode/{barcode}")
    
    return response

def create_sale(items: list, payment_method):
    payload = {
        "payment_method": payment_method,
        "items": items
    }

    return api_request("POST", f"{API_URL}/sales", json=payload) is not None

def search_products(name: str):
    response = api_request("GET", f"{API_URL}/products", params={"search": name})
    
    return response or []



def list_sales(start_date = None, end_date = None, limit= 20, offset = 0):

    params = {
        "limit": limit,
        "offset": offset
    }

    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    response = api_request("GET", f"{API_URL}/sales", params=params)
    return response or []