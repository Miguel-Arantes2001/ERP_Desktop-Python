from sqlalchemy import Column, Float, Integer, String, ForeignKey, DateTime, func  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import relationship, declarative_base  # pyright: ignore[reportMissingImports]
from datetime import datetime
from database import Base
from zoneinfo import ZoneInfo

def now_brazil():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))



class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cnpj = Column(String, unique=True, nullable=False)

    users = relationship("User", back_populates="store")
    products = relationship("Product", back_populates="store")
    sales = relationship("Sale", back_populates="store")
    logo_url = Column(String, nullable=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True,index=True)
    email = Column(String, unique=True)
    password = Column(String)

    store_id = Column(Integer, ForeignKey("stores.id"))
    store = relationship("Store",back_populates="users")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    barcode = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Float, nullable=True, default=None)
    unit_of_measure = Column(String, default="un")  # un | kg | m
    image_path = Column(String, nullable=True)

    store = relationship("Store", back_populates="products")


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)

    store_id = Column(Integer, ForeignKey("stores.id"))
    total = Column(Float)
    payment_method = Column(String)
    created_at = Column(DateTime, default=now_brazil)

    store = relationship("Store", back_populates="sales")
    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy = "subquery"
    )


class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)

    sale_id = Column(Integer, ForeignKey("sales.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    description = Column(String, nullable=True)

    quantity = Column(Float)
    price = Column(Float)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

    @property
    def product_name(self):
        if self.product:
            return self.product.name
        return self.description

    @property
    def unit_of_measure(self):
        return self.product.unit_of_measure if self.product else "un"

    @property
    def item_type(self):
        return "generic" if self.product_id is None else "product"


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)

    product_id = Column(Integer, ForeignKey("products.id"))
    type = Column(String)  # in | out
    quantity = Column(Float)
    reason = Column(String)
    created_at = Column(DateTime, default=now_brazil)

    product = relationship("Product")



