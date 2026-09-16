from fastapi import Depends 
from sqlalchemy.orm import Session 
from database import get_db
from auth import get_current_user
from fastapi import APIRouter
from models import Sale, SaleItem, Product, User,StockMovement, now_brazil
from datetime import datetime
from zoneinfo import ZoneInfo
from schemas import SaleSchema, SaleCreateSchema
from fastapi import HTTPException  
from typing import List


sales_router = APIRouter(prefix="/sales",tags=['sales'])

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def _resolve_sale_datetime(sold_at: datetime | None) -> datetime:
    if sold_at is None:
        return now_brazil()

    sale_datetime = sold_at
    if sale_datetime.tzinfo is None:
        sale_datetime = sale_datetime.replace(tzinfo=BRAZIL_TZ)

    if sale_datetime > now_brazil():
        raise HTTPException(
            status_code=400,
            detail="A data da venda não pode ser no futuro"
        )

    return sale_datetime


@sales_router.post("")
async def create_sale(sale: SaleCreateSchema, db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)):
    total = 0
    sale_datetime = _resolve_sale_datetime(sale.sold_at)

    new_sale = Sale(
        payment_method=sale.payment_method,
        total=0,
        store_id=current_user.store_id,
        created_at=sale_datetime,
    )

    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)

    for item in sale.items:
        product = None

        if item.product_id:
            product = db.query(Product).filter(
                Product.id == item.product_id,
                Product.store_id == current_user.store_id
            ).first()

        if not product and item.barcode:
            product = db.query(Product).filter(
                Product.barcode == item.barcode,
                Product.store_id == current_user.store_id
            ).first()


            if not product:
                if not item.name or item.price is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Dados incompletos para cadastrar o produto do código {item.barcode}"
                    )

                product = Product(
                    barcode=item.barcode,
                    name=item.name,
                    price=item.price,
                    stock=None,
                    unit_of_measure=item.unit_of_measure,
                    store_id=current_user.store_id
                )
                db.add(product)
                db.flush()


        if not product:
            is_generic = (
                not item.product_id
                and not (item.barcode and item.barcode.strip())
                and item.name
                and item.price is not None
            )
            if is_generic:
                description = item.name.strip()
                item_price = item.price
                total += item_price * item.quantity
                db.add(SaleItem(
                    sale_id=new_sale.id,
                    product_id=None,
                    description=description,
                    quantity=item.quantity,
                    price=item_price,
                ))
                continue

            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado e sem dados suficientes para cadastro."
            )

        if product.stock is not None:

            if item.quantity > product.stock:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Estoque insuficiente para '{product.name}'. "
                        f"Disponível: {product.stock}"
                    )
                )

            product.stock -= item.quantity


        item_price = item.price if item.price is not None else product.price
        subtotal = item_price * item.quantity
        total += subtotal

        sale_item = SaleItem(
            sale_id=new_sale.id,
            product_id=product.id,
            quantity=item.quantity,
            price=item_price
        )
        db.add(sale_item)

        stock_movement = StockMovement(
            product_id=product.id,
            type="out",
            quantity=item.quantity,
            reason=f"Venda #{new_sale.id}",
            created_at=sale_datetime,
        )
        db.add(stock_movement)

    new_sale.total = total
    db.commit()

    return {
        "sale_id": new_sale.id,
        "total": total,
        "payment_method": sale.payment_method
    }


@sales_router.get("", response_model=List[SaleSchema])
async def list_sales(
    limit: int = 20,
    offset: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        db.query(Sale)
        .filter(Sale.store_id == current_user.store_id)
    )

    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(Sale.created_at >= start)

    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(Sale.created_at <= end)


    return (
        query
        .order_by(Sale.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


  

@sales_router.get("/{sale_id}")
async def get_sale(sale_id: int, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    sale = (
        db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.store_id == current_user.store_id
        ).first()
    )
    if not sale:
        raise HTTPException(404,"Venda não encontrada")

    return sale


def _restore_stock_from_sale(sale: Sale, db: Session) -> None:
    for item in sale.items:
        if item.product_id is None:
            continue

        product = item.product
        if product is not None and product.stock is not None:
            product.stock += item.quantity

    movements = (
        db.query(StockMovement)
        .filter(
            StockMovement.reason == f"Venda #{sale.id}",
            StockMovement.type == "out",
        )
        .all()
    )
    for movement in movements:
        db.delete(movement)


@sales_router.delete("/{sale_id}")
async def delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sale = (
        db.query(Sale).filter(
            Sale.id == sale_id,
            Sale.store_id == current_user.store_id
        ).first()
    )
    if not sale:
        raise HTTPException(404, "Venda não encontrada")

    _restore_stock_from_sale(sale, db)
    db.delete(sale)
    db.commit()

    return {
        "deleted_sale_id": sale_id,
        "message": "Venda apagada e estoque estornado",
    }
