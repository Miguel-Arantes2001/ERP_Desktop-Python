
from services.api import API_URL, get_headers,api_request


def get_sales_summary(start_date: str, end_date: str):
    response = api_request("GET", f"{API_URL}/reports/sales/summary", params={
        "start": start_date,
            "end": end_date
        }
    )
    return response or {'total_sales': 0}

def get_top_products():
     return api_request("GET", f"{API_URL}/reports/products/top") or []


def get_sales_by_payment():
    return api_request("GET", f"{API_URL}/reports/sales/by-payment") or []