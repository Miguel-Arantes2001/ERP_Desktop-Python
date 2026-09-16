
from fastapi import Depends ,APIRouter # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session # pyright: ignore[reportMissingImports]
from auth import get_current_user
from database import get_db
from models import Sale, SaleItem, Product, User
from datetime import datetime, timezone, timedelta
from sqlalchemy import func  # pyright: ignore[reportMissingImports]


reports_router = APIRouter(prefix="/reports",tags=['reports'])

@reports_router.get("/sales/summary")
async def sales_summary(
    start: str,
    end: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_date = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    end_date = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)

    result = (
        db.query(
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count"),
        )
        .filter(Sale.store_id == current_user.store_id)
        .filter(Sale.created_at >= start_date)
        .filter(Sale.created_at < end_date)
        .first()
    )

    total = result.total or 0
    count = result.count or 0
    average_ticket = (total / count) if count else 0

    top_row = (
        db.query(
            Product.name.label("name"),
            Product.unit_of_measure.label("unit_of_measure"),
            func.sum(SaleItem.quantity).label("quantity_sold"),
            func.sum(SaleItem.quantity * SaleItem.price).label("revenue"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.store_id == current_user.store_id)
        .filter(Sale.created_at >= start_date)
        .filter(Sale.created_at < end_date)
        .group_by(Product.id, Product.name, Product.unit_of_measure)
        .order_by(func.sum(SaleItem.quantity * SaleItem.price).desc())
        .first()
    )

    top_product = None
    if top_row is not None:
        quantity_sold = float(top_row.quantity_sold or 0)
        revenue = float(top_row.revenue or 0)
        unit_price = (revenue / quantity_sold) if quantity_sold else 0
        top_product = {
            "name": top_row.name,
            "quantity_sold": quantity_sold,
            "unit_of_measure": top_row.unit_of_measure or "un",
            "unit_price": unit_price,
            "revenue": revenue,
        }

    return {
        "start": start,
        "end": end,
        "total_sales": total,
        "sale_count": count,
        "average_ticket": average_ticket,
        "top_product": top_product,
    }


@reports_router.get("/products/top")
async def top_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = (
        db.query(
            Product.name.label("product"),
            Product.unit_of_measure.label("unit_of_measure"),
            func.sum(SaleItem.quantity).label("quantity_sold")
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.store_id == current_user.store_id)
        .group_by(Product.id, Product.name, Product.unit_of_measure)
        .order_by(func.sum(SaleItem.quantity).desc())
        .all()
    )

    return [
        {
            "product": row.product,
            "quantity_sold": row.quantity_sold,
            "unit_of_measure": row.unit_of_measure or "un",
        }
        for row in result
    ]



@reports_router.get("/sales/by-payment")
async def sales_by_payment(db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = (
        db.query(
            Sale.payment_method,
            func.sum(Sale.total).label("total")
        ).filter(Sale.store_id == current_user.store_id)

        .group_by(Sale.payment_method)
        .all()
    )

    return [
        {
            "payment_method": row.payment_method,
            "total": row.total
        }
        for row in result
    ]