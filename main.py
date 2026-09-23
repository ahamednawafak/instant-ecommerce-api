import os
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

# --- 1. SECURITY & CONFIGURATION ---
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --- 2. DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecommerce.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 3. DATABASE MODELS ---
class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    stores = relationship("DBStore", back_populates="owner")


class DBStore(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    whatsapp_number = Column(String)
    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)

    owner = relationship("DBUser", back_populates="stores")
    products = relationship("DBProduct", back_populates="store")


class DBProduct(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    category = Column(String, default="General", index=True)
    in_stock = Column(Boolean, default=True)

    store = relationship("DBStore", back_populates="products")


Base.metadata.create_all(bind=engine)


# Auto Migration for PostgreSQL
def run_auto_migrations():
    db = SessionLocal()
    try:
        if "postgresql" in DATABASE_URL:
            db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR DEFAULT 'General';"))
            db.execute(text("ALTER TABLE stores ADD COLUMN IF NOT EXISTS owner_id INTEGER;"))
            db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

run_auto_migrations()


# --- 4. SCHEMAS ---
class UserRegister(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = "General"
    in_stock: bool = True

class ProductResponse(ProductCreate):
    id: int
    store_id: int

    class Config:
        from_attributes = True

class StoreCreate(BaseModel):
    name: str
    slug: str
    whatsapp_number: str
    currency: str = "USD"

class StoreResponse(StoreCreate):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class CartItem(BaseModel):
    product_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: str
    notes: Optional[str] = None
    items: List[CartItem]


# --- 5. HELPERS & AUTH DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> DBUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# --- 6. FASTAPI APP & CORS ---
app = FastAPI(title="Instant E-Commerce WhatsApp API (JWT Secured)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Welcome to the Instant WhatsApp E-Commerce API!"}


# --- 7. AUTHENTICATION ENDPOINTS ---
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_owner(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(DBUser).filter(DBUser.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered.")
    
    new_user = DBUser(
        username=user_data.username,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Account created successfully!", "username": new_user.username}

@app.post("/auth/login", response_model=TokenResponse)
def login_owner(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


# --- 8. STORE MANAGEMENT (PROTECTED) ---
@app.post("/stores", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(
    store: StoreCreate, 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    existing = db.query(DBStore).filter(DBStore.slug == store.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Store slug already exists.")
    
    db_store = DBStore(**store.model_dump(), owner_id=current_user.id)
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    return db_store

@app.get("/stores/{slug}", response_model=StoreResponse)
def get_store(slug: str, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug, DBStore.is_active == True).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    return store


# --- 9. PRODUCT CATALOG (PROTECTED MANAGEMENT / PUBLIC READING) ---
@app.post("/stores/{slug}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    slug: str, 
    product: ProductCreate, 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    # Verify the logged in user owns the store
    if store.owner_id and store.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this store.")

    db_product = DBProduct(**product.model_dump(), store_id=store.id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/stores/{slug}/products", response_model=List[ProductResponse])
def list_products(slug: str, category: Optional[str] = None, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    query = db.query(DBProduct).filter(DBProduct.store_id == store.id, DBProduct.in_stock == True)
    if category:
        query = query.filter(DBProduct.category == category)
        
    return query.all()

@app.get("/stores/{slug}/categories")
def list_categories(slug: str, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    categories = db.query(DBProduct.category).filter(
        DBProduct.store_id == store.id, 
        DBProduct.in_stock == True
    ).distinct().all()
    
    return [c[0] for c in categories if c[0]]


# --- 10. PUBLIC WHATSAPP CHECKOUT ENGINE ---
@app.post("/stores/{slug}/checkout/whatsapp")
def generate_whatsapp_order_link(slug: str, checkout: CheckoutRequest, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    if not checkout.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")

    order_items_text = ""
    total_price = 0.0

    for item in checkout.items:
        product = db.query(DBProduct).filter(DBProduct.id == item.product_id, DBProduct.store_id == store.id).first()
        if not product:
            raise HTTPException(status_code=400, detail=f"Product ID {item.product_id} not found in this store.")
        
        item_total = product.price * item.quantity
        total_price += item_total
        order_items_text += f"• {item.quantity}x {product.name} ({store.currency} {item_total:.2f})\n"

    message = (
        f"🛍️ *NEW ORDER - {store.name.upper()}*\n"
        f"----------------------------------------\n"
        f"👤 *Customer:* {checkout.customer_name}\n"
        f"📞 *Phone:* {checkout.customer_phone}\n"
        f"📍 *Address:* {checkout.delivery_address}\n"
    )
    
    if checkout.notes:
        message += f"📝 *Notes:* {checkout.notes}\n"

    message += (
        f"----------------------------------------\n"
        f"*ITEMS ORDERED:*\n{order_items_text}"
        f"----------------------------------------\n"
        f"💰 *TOTAL AMOUNT:* {store.currency} {total_price:.2f}\n"
        f"💳 *Payment Method:* Cash on Delivery / Instant Transfer\n\n"
        f"Please confirm availability and estimated delivery time! Thank you."
    )

    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/{store.whatsapp_number}?text={encoded_message}"

    return {
        "store_name": store.name,
        "total_amount": total_price,
        "currency": store.currency,
        "raw_message": message,
        "whatsapp_redirect_url": whatsapp_url
    }