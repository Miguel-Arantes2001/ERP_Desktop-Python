from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal
from pydantic import ConfigDict  
from datetime import datetime

UnitOfMeasure = Literal["un", "kg", "m"]


class ProductBaseSchema(BaseModel):
    name: str
    barcode: str | None = None
    price: float
    stock: float  | None = None
    unit_of_measure: UnitOfMeasure = "un"
    description: str | None = None


class ProductCreateSchema(BaseModel):
    name: str
    barcode: str | None = None 
    price: float
    stock: float | None = None
    unit_of_measure: UnitOfMeasure = "un"
    description: str | None = None


class SaleItemCreateSchema(BaseModel):
    product_id: Optional[int] = None
    quantity: float = Field(gt=0)
    barcode: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    unit_of_measure: UnitOfMeasure = "un"

    @model_validator(mode="after")
    def validate_item_identity(self):
        has_product_ref = (
            self.product_id is not None
            or (self.barcode is not None and self.barcode.strip() != "")
        )
        has_generic = (
            self.name is not None
            and self.name.strip() != ""
            and self.price is not None
        )
        if not has_product_ref and not has_generic:
            raise ValueError(
                "Informe um produto cadastrado ou uma descrição e valor "
                "para venda rápida."
            )
        if has_generic and not has_product_ref and self.price is not None and self.price <= 0:
            raise ValueError("O valor da venda rápida deve ser maior que zero.")
        return self


class SaleCreateSchema(BaseModel):
    payment_method: str
    items: List[SaleItemCreateSchema]
    sold_at: Optional[datetime] = None


class ProductResponseSchema(ProductBaseSchema):
    id: int
    store_id: int
    image_path: str | None = None
    model_config = ConfigDict(from_attributes=True)


class SaleItemResponseSchema(BaseModel):
    product_id: int | None = None
    product_name: str | None = None
    description: str | None = None
    quantity: float
    price: float
    unit_of_measure: str = "un"
    item_type: Literal["product", "generic"] = "product"

    model_config = ConfigDict(from_attributes=True)


class SaleSchema(BaseModel):
    id: int
    total: float
    payment_method: str
    created_at: datetime
    items: list[SaleItemResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class UserCreateSchema(BaseModel):
    email: str
    password: str
    store_name: str
    cnpj: str
    logo_url: str|None = None

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str



class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class AccessTokenSchema(BaseModel):
    access_token: str
    token_type: str


class AddstockRequestSchema(BaseModel):
    quantity: float = Field(gt=0)
    reason: Optional[str] = None


class ProductBarcodeUpdateSchema(BaseModel):
    barcode: str


class ProductUpdateSchema(BaseModel):
    name: str | None = None
    price: float | None = None
    description: str | None = None
    unit_of_measure: UnitOfMeasure | None = None
