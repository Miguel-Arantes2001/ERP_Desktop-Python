from pydantic import BaseModel
from typing import List, Optional
from pydantic import ConfigDict
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    barcode: str
    price: float
    stock: int
    description: str | None = None


class ProductCreate(BaseModel):
    name: str
    barcode: str
    price: float
    stock: int
    description: str | None = None

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int

class SaleCreate(BaseModel):
    payment_method: str
    items: List[SaleItemCreate]    

class Product(ProductCreate):
    id: int
    store_id: int
    model_config = ConfigDict(from_attributes=True)


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    price: float

    model_config = ConfigDict(from_attributes=True)


class Sale(BaseModel):
    id: int
    total: float
    payment_method: str
    created_at: datetime
    items: list[SaleItem]

    model_config = ConfigDict(from_attributes=True)

## AUTENTICAÇÃO

class UserCreate(BaseModel):
    email: str
    password: str
    store_name: str
    cnpj: str
    logo_url: str|None = None

class Token(BaseModel):
    access_token: str
    token_type: str


class AddstockRequest(BaseModel):
    quantity: int
    reason:Optional[str] = None

