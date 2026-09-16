from fastapi import Depends, HTTPException,APIRouter
from sqlalchemy.orm import Session # pyright: ignore[reportMissingImports]
from fastapi.security import OAuth2PasswordRequestForm  
from database import get_db
from schemas import TokenSchema, UserCreateSchema,AccessTokenSchema,RefreshTokenRequestSchema
from models import User, Store
from auth import hash_password, create_access_token ,create_refresh_token , get_current_user,verify_password, decode_refresh_token




auth_router = APIRouter(prefix="/auth", tags = ['auth'])

@auth_router.post("/register")
async def register(user: UserCreateSchema, db: Session = Depends(get_db)):
    store = Store(name=user.store_name,cnpj=user.cnpj,logo_url=user.logo_url)
    
    db.add(store)
    db.commit()
    db.refresh(store)

    db_user = User(
        email=user.email,
        password=hash_password(user.password),
        store_id=store.id
        
    )

    db.add(db_user)
    db.commit()

    return {"message": "Usuário e loja criados com sucesso"}


from auth import verify_password

@auth_router.post("/login",response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.strip()
    password = form_data.password.strip()
    
    user = db.query(User).filter(User.email == email).first()

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

    refresh_token = create_refresh_token(
        data = {
            "sub" : str(user.id)
        }
    )

    return {
        "access_token": access_token,
        "refresh_token":refresh_token,
        "token_type": "bearer"
    }


@auth_router.post('/refresh', response_model= AccessTokenSchema)
async def refresh_token(
    payload : RefreshTokenRequestSchema,
    db: Session = Depends(get_db)
):
    data = decode_refresh_token(payload.refresh_token)
    user_id = data.get('sub') 

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")

    new_access_token = create_access_token(
        data={
            "sub": str(user.id),
            "store_id": user.store_id
        }
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }

@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user),
       db: Session = Depends(get_db)):
    
    store = db.query(Store).filter(Store.id == current_user.store_id).first()

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


