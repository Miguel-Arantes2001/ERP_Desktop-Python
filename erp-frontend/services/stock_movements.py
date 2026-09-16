import requests
from services.api import API_URL, get_headers,api_request

def list_stock_movements(start_date=None, end_date=None,limit=None,offset=None):
    params = {}

    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    response = api_request(
        "GET",
        f"{API_URL}/stock-movements",
        params=params
    )

    return response or []