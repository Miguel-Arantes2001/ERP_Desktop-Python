from sqlalchemy import Column, Float, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, declarative_base
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
    stock = Column(Integer, default=0)

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
    product_id = Column(Integer, ForeignKey("products.id"))

    quantity = Column(Integer)
    price = Column(Float)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(Integer, primary_key=True)

    product_id = Column(Integer, ForeignKey("products.id"))
    type = Column(String)  # in | out
    quantity = Column(Integer)
    reason = Column(String)
    created_at = Column(DateTime, default=now_brazil)

    product = relationship("Product")



