from fastapi import Depends, APIRouter # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session # pyright: ignore[reportMissingImports]
from database import get_db
from auth import get_current_user
from models import StockMovement, Product, User
from datetime import datetime
from sqlalchemy.orm import joinedload # pyright: ignore[reportMissingImports]



stock_movements_router = APIRouter(prefix="/stock-movements",tags=['stock-movements'])

@stock_movements_router.get("")
async def list_stock_movements(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    

    query = (
        db.query(StockMovement)
        .join(Product)
        .filter(Product.store_id == current_user.store_id)
        .options(joinedload(StockMovement.product))
        .order_by(StockMovement.created_at.desc())
    )

    if start_date:
        query = query.filter(
            StockMovement.created_at >= datetime.fromisoformat(start_date)
        )

    if end_date:
        query = query.filter(
            StockMovement.created_at <= datetime.fromisoformat(end_date)
        )

    movements = query.all()

    return [
        {
            "id": m.id,
            "type": m.type,
            "quantity": m.quantity,
            "reason": m.reason,
            "created_at": m.created_at.isoformat(),
            "product": {
                "id": m.product.id,
                "name": m.product.name,
                "barcode": m.product.barcode,
                "unit_of_measure": m.product.unit_of_measure or "un",
            }
        }
        for m in movements
    ]
