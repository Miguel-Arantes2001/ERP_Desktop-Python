from fastapi import Depends, HTTPException ,APIRouter# pyright: ignore[reportMissingImports]
from sqlalchemy.orm import Session # pyright: ignore[reportMissingImports]
from auth import get_current_user, create_photo_token, PHOTO_TOKEN_EXPIRE_MINUTES
from database import get_db
from schemas import (
    ProductCreateSchema,
    AddstockRequestSchema,
    ProductBarcodeUpdateSchema,
    ProductUpdateSchema,
    ProductResponseSchema,
)
from models import Product, StockMovement, User
from typing import List
from http import HTTPStatus


products_router = APIRouter(prefix="/products",tags=['products'])


def _is_placeholder_barcode(barcode: str | None) -> bool:
    if not barcode or not barcode.strip():
        return True
    return barcode.strip().upper().startswith("INT-")


def _normalize_barcode(barcode: str | None) -> str:
    value = (barcode or "").strip()
    if _is_placeholder_barcode(value):
        return ""
    return value


def _get_product_for_store(
    product_id: int,
    store_id: int,
    db: Session
) -> Product:
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == store_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado"
        )

    return product


def _ensure_unique_barcode(
    barcode: str,
    store_id: int,
    db: Session,
    exclude_product_id: int | None = None
):
    query = db.query(Product).filter(
        Product.barcode == barcode,
        Product.store_id == store_id
    )

    if exclude_product_id is not None:
        query = query.filter(Product.id != exclude_product_id)

    if query.first():
        raise HTTPException(
            status_code=400,
            detail="Já existe um produto com este código de barras"
        )


@products_router.post("", status_code=HTTPStatus.CREATED)
async def create_product(
    product: ProductCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    barcode = _normalize_barcode(product.barcode)
    if barcode:
        _ensure_unique_barcode(barcode, current_user.store_id, db)

    p = Product(
        name=product.name.strip(),
        barcode=barcode,
        price=product.price,
        stock=product.stock,
        unit_of_measure=product.unit_of_measure,
        store_id=current_user.store_id,
        description=product.description
    )

    db.add(p)
    db.commit()
    db.refresh(p)

    if p.stock is not None and p.stock > 0:
        movement = StockMovement(
            product_id=p.id,
            type="in",
            quantity=p.stock,
            reason="Estoque inicial"
        )

        db.add(movement)
        db.commit()

    return p


@products_router.get("", response_model=List[ProductResponseSchema])
async def list_products(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    query = db.query(Product).filter(
        Product.store_id == current_user.store_id
    )

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
        )

    return query.all()


@products_router.get(
    "/{product_id}",
    response_model=ProductResponseSchema,
)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_product_for_store(product_id, current_user.store_id, db)


@products_router.post("/{product_id}/photo-session")
async def create_product_photo_session(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = _get_product_for_store(product_id, current_user.store_id, db)
    token = create_photo_token(product.id, current_user.store_id)
    return {
        "token": token,
        "expires_in": PHOTO_TOKEN_EXPIRE_MINUTES * 60,
        "product_name": product.name,
        "image_path": product.image_path,
    }


@products_router.post(
    "/{product_id}/rotate-photo",
    response_model=ProductResponseSchema,
)
async def rotate_product_photo(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from pathlib import Path
    from PIL import Image
    import time

    product = _get_product_for_store(product_id, current_user.store_id, db)
    if not product.image_path:
        raise HTTPException(status_code=400, detail="Este produto não tem foto")

    static_root = Path(__file__).resolve().parent.parent / "static"
    source = static_root / product.image_path
    if not source.is_file():
        raise HTTPException(status_code=404, detail="Arquivo da foto não encontrado")

    image = Image.open(source)
    image.load()
    image = image.rotate(-90, expand=True)
    if image.mode != "RGB":
        image = image.convert("RGB")

    relative = f"products/{product.store_id}/{product.id}_{int(time.time())}.jpg"
    dest = static_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, format="JPEG", quality=85, optimize=True)

    if source != dest:
        try:
            source.unlink()
        except OSError:
            pass

    product.image_path = relative.replace("\\", "/")
    db.commit()
    db.refresh(product)
    return product


@products_router.post(
    "/{product_id}/add-stock",
    status_code=HTTPStatus.OK
)
async def add_stock(
    product_id: int,
    data: AddstockRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == current_user.store_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Produto não encontrado"
        )

    if data.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantidade inválida"
        )

    estoque_atual = (
        product.stock
        if product.stock is not None
        else 0
    )

    product.stock = estoque_atual + data.quantity

    movement = StockMovement(
        product_id=product.id,
        type="in",
        quantity=data.quantity,
        reason=data.reason or "Entrada manual de estoque"
    )

    db.add(movement)
    db.commit()
    db.refresh(product)

    return {
        "message": "Estoque atualizado com sucesso",
        "product_id": product.id,
        "new_stock": product.stock
    }


@products_router.patch(
    "/{product_id}",
    response_model=ProductResponseSchema
)
async def update_product(
    product_id: int,
    data: ProductUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = _get_product_for_store(
        product_id,
        current_user.store_id,
        db
    )

    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(
                status_code=400,
                detail="O nome do produto não pode ficar vazio"
            )
        product.name = name

    if data.price is not None:
        if data.price < 0:
            raise HTTPException(
                status_code=400,
                detail="O preço não pode ser negativo"
            )
        product.price = data.price

    if data.description is not None:
        product.description = data.description

    if data.unit_of_measure is not None:
        product.unit_of_measure = data.unit_of_measure

    db.commit()
    db.refresh(product)
    return product


@products_router.patch(
    "/{product_id}/barcode",
    response_model=ProductResponseSchema
)
async def update_product_barcode(
    product_id: int,
    data: ProductBarcodeUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = _get_product_for_store(
        product_id,
        current_user.store_id,
        db
    )

    barcode = _normalize_barcode(data.barcode)

    if barcode == (product.barcode or ""):
        return product

    if barcode:
        _ensure_unique_barcode(
            barcode,
            current_user.store_id,
            db,
            exclude_product_id=product.id
        )

    product.barcode = barcode
    db.commit()
    db.refresh(product)

    return product


@products_router.get("/barcode/{barcode}")
async def get_product_by_barcode(barcode: str, db: Session = Depends(get_db)
                           , current_user: User = Depends(get_current_user)):
    
    return db.query(Product).filter(
        Product.barcode == barcode,
        Product.store_id == current_user.store_id
    ).first()


@products_router.delete('/delete/{product_id}',status_code=HTTPStatus.OK)
async def delete_product(product_id:int,db = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = _get_product_for_store(product_id,current_user.store_id,db)
    db.delete(product)
    db.commit()
    return {
        "message": "Produto deletado com sucesso"
    }
    