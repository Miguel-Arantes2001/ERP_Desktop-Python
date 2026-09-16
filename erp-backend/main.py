from fastapi import FastAPI, Depends, status, HTTPException  
from fastapi.security import OAuth2PasswordRequestForm ,OAuth2PasswordBearer
import models
from database import engine
from migrate import run_migrations
from fastapi.staticfiles import StaticFiles  
from dotenv import load_dotenv
import os
from passlib.context import CryptContext

run_migrations()
models.Base.metadata.create_all(bind=engine)  

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(os.path.join(STATIC_DIR, "products"), exist_ok=True)

from routes.products_routes import products_router
from routes.sales_routes import sales_router
from routes.stock_movements_routes import stock_movements_router
from routes.reports_routes import reports_router
from routes.auth_routes import auth_router
from routes.photo_routes import photo_router


app.include_router(auth_router)
app.include_router(sales_router)
app.include_router(stock_movements_router)
app.include_router(reports_router)
app.include_router(products_router)
app.include_router(photo_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")






