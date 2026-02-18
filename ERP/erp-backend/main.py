from fastapi import FastAPI, Depends, status, HTTPException
from sqlalchemy.orm import Session,joinedload
from database import SessionLocal, engine
import models, schemas
from typing import List
from datetime import datetime, time, timedelta, timezone
from sqlalchemy import func
from auth import get_current_user
from database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from schemas import AddstockRequest

from fastapi.staticfiles import StaticFiles

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
    
# =====================
# PRODUCTS
# =====================
@app.post("/products",status_code=status.HTTP_201_CREATED)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    p = models.Product(
        name=product.name,
        barcode=product.barcode,
        price=product.price,
        stock=product.stock,
        store_id=current_user.store_id, 
        description=product.description
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    

    if p.stock > 0: # type: ignore
        movement = models.StockMovement(
            product_id=p.id,
            type="in",
            quantity=p.stock,
            reason="Estoque inicial"
        )
        db.add(movement)
        db.commit()

    return p


@app.get("/products", response_model=List[schemas.Product])
def list_products(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):

    query = db.query(models.Product).filter(
        models.Product.store_id == current_user.store_id
    )

    if search:
        query = query.filter(
            models.Product.name.ilike(f"%{search}%")
        )

    return query.all()


@app.post("/products/{product_id}/add-stock")
def add_stock(
    product_id: int,
    data: AddstockRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.store_id == current_user.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if data.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantidade inválida")

    product.stock += data.quantity # type: ignore

    movement = models.StockMovement(
        product_id=product.id,
        type="in",
        quantity=data.quantity,
        reason=data.reason or "Entrada manual de estoque"
    )

    db.add(movement)
    db.commit()

    return {
        "message": "Estoque atualizado com sucesso",
        "product_id": product.id,
        "new_stock": product.stock
    }

# =====================
# SALES / PDV
# =====================
from fastapi import HTTPException

@app.post("/sales")
def create_sale(sale: schemas.SaleCreate, db: Session = Depends(get_db), 
                current_user: models.User = Depends(get_current_user)):
    total = 0

    new_sale = models.Sale(
        payment_method=sale.payment_method,
        total=0,
        store_id=current_user.store_id
    )

    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)

    for item in sale.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id,
            models.Product.store_id == current_user.store_id
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail="Produto não encontrado"
            )

        if product.stock < item.quantity: # type: ignore
            raise HTTPException(
                status_code=400,
                detail=f"Estoque insuficiente para {product.name}"
            )

        # baixa estoque
        product.stock -= item.quantity # type: ignore

        subtotal = product.price * item.quantity
        total += subtotal

        sale_item = models.SaleItem(
            sale_id=new_sale.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price
        )

        db.add(sale_item)

        stock_movement = models.StockMovement(
            product_id=product.id,
            type="out",
            quantity=item.quantity,
            reason=f"Venda #{new_sale.id}"
        )

        db.add(stock_movement)

    new_sale.total = total # type: ignore
    db.commit()

    return {
        "sale_id": new_sale.id,
        "total": total,
        "payment_method": sale.payment_method
    }


@app.get("/sales", response_model=List[schemas.Sale])
def list_sales(
    limit: int = 20,
    offset: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = (
        db.query(models.Sale)
        .filter(models.Sale.store_id == current_user.store_id)
        # .options(joinedload(models.Sale.items))
    )

    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(models.Sale.created_at >= start)

    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(models.Sale.created_at <= end)


    return (
        query
        .order_by(models.Sale.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


  

@app.get("/sales/{sale_id}")
def get_sale(sale_id: int, db: Session = Depends(get_db),current_user: models.User = Depends(get_current_user)):
    sale = (
        db.query(models.Sale).filter(
            models.Sale.id == sale_id,
            models.Sale.store_id == current_user.store_id
        ).first()
    )
    if not sale:
        raise HTTPException(404,"Venda não encontrada")

    return sale
        


@app.get("/stock-movements")
def list_stock_movements(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    

    query = (
        db.query(models.StockMovement)
        .join(models.Product)
        .filter(models.Product.store_id == current_user.store_id)
        .options(joinedload(models.StockMovement.product))
        .order_by(models.StockMovement.created_at.desc())
    )

    if start_date:
        query = query.filter(
            models.StockMovement.created_at >= datetime.fromisoformat(start_date)
        )

    if end_date:
        query = query.filter(
            models.StockMovement.created_at <= datetime.fromisoformat(end_date)
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
                "barcode": m.product.barcode
            }
        }
        for m in movements
    ]



@app.get("/products/barcode/{barcode}")
def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)
                           , current_user: models.User = Depends(get_current_user)):
    
    return db.query(models.Product).filter(
        models.Product.barcode == barcode,
        models.Product.store_id == current_user.store_id
    ).first()


# =====================
# Base para dashboard

@app.get("/reports/sales/summary")
def sales_summary(
    start: str,
    end: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    start_date = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    end_date = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)+timedelta(days=1)

    total = (
        db.query(func.sum(models.Sale.total)).filter(models.Sale.store_id == current_user.store_id)
        .filter(models.Sale.created_at >= start_date)
        .filter(models.Sale.created_at < end_date)
        .scalar()
    )

    return {
        "start": start,
        "end": end,
        "total_sales": total or 0
    }


@app.get("/reports/products/top")
def top_products(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    result = (
        db.query(
            models.Product.name.label("product"),
            func.sum(models.SaleItem.quantity).label("quantity_sold")
        )
        .join(models.SaleItem, models.SaleItem.product_id == models.Product.id)
        .join(models.Sale, models.Sale.id == models.SaleItem.sale_id)
        .filter(models.Sale.store_id == current_user.store_id)
        .group_by(models.Product.id, models.Product.name)
        .order_by(func.sum(models.SaleItem.quantity).desc())
        .all()
    )

    return [
        {
            "product": row.product,
            "quantity_sold": row.quantity_sold
        }
        for row in result
    ]



@app.get("/reports/sales/by-payment")
def sales_by_payment(db: Session = Depends(get_db),current_user: models.User = Depends(get_current_user)):
    result = (
        db.query(
            models.Sale.payment_method,
            func.sum(models.Sale.total).label("total")
        ).filter(models.Sale.store_id == current_user.store_id)

        .group_by(models.Sale.payment_method)
        .all()
    )

    return [
        {
            "payment_method": row.payment_method,
            "total": row.total
        }
        for row in result
    ]

## ENDPOINT DE CADASTRO 

from auth import hash_password, create_access_token

@app.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    store = models.Store(name=user.store_name,cnpj=user.cnpj,logo_url=user.logo_url)
    
    db.add(store)
    db.commit()
    db.refresh(store)

    db_user = models.User(
        email=user.email,
        password=hash_password(user.password),
        store_id=store.id
        
    )

    db.add(db_user)
    db.commit()

    return {"message": "Usuário e loja criados com sucesso"}


## LOGIN

from auth import verify_password

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.strip()
    password = form_data.password.strip()
    
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    if not verify_password(password, user.password): # type: ignore
        raise HTTPException(status_code=400, detail="Senha incorreta")

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "store_id": user.store_id
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.get("/me")
def me(current_user: models.User = Depends(get_current_user),
       db: Session = Depends(get_db)):
    
    store = db.query(models.Store).filter(models.Store.id == current_user.store_id).first()

    if not store:
        raise HTTPException(status_code=500, detail="Loja não encontrada")


    return {
        "id": current_user.id,
        "email": current_user.email,
        "store": {
            "id": store.id,
            "name": store.name,
            "cnpj": store.cnpj,
            "logo_url": store.logo_url
        }
    }


