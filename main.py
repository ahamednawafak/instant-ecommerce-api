import os
from urllib.parse import quote
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# --- 1. DATABASE SETUP (PostgreSQL / SQLite Fallback) ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ecommerce.db")

# Render uses 'postgres://' prefixes, but SQLAlchemy 2.0+ requires 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- 2. DATABASE MODELS ---
class DBStore(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)  # e.g. "ahamed-bakery"
    whatsapp_number = Column(String)  # Format without + (e.g. 97455551234)
    currency = Column(String, default="USD")
    is_active = Column(Boolean, default=True)

    products = relationship("DBProduct", back_populates="store")


class DBProduct(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    category = Column(String, default="General", index=True)  # Category support
    in_stock = Column(Boolean, default=True)

    store = relationship("DBStore", back_populates="products")


Base.metadata.create_all(bind=engine)


# --- 3. SCHEMAS (Pydantic Models) ---
class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = "General"  # e.g., Cakes, Pastries, Beverages
    in_stock: bool = True

class ProductResponse(ProductCreate):
    id: int
    store_id: int

    class Config:
        from_attributes = True

class StoreCreate(BaseModel):
    name: str
    slug: str
    whatsapp_number: str  # Format: 97455551234
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


# --- 4. DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 5. FASTAPI APP & CORS MIDDLEWARE ---
app = FastAPI(title="Instant E-Commerce WhatsApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows frontend websites to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 6. ENDPOINTS ---

@app.get("/")
def home():
    return {"message": "Welcome to the Instant WhatsApp E-Commerce API!"}


# --- STORE MANAGEMENT ---
@app.post("/stores", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
def create_store(store: StoreCreate, db: Session = Depends(get_db)):
    existing = db.query(DBStore).filter(DBStore.slug == store.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Store slug already exists.")
    
    db_store = DBStore(**store.model_dump())
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


# --- PRODUCT CATALOG & CATEGORIES ---
@app.post("/stores/{slug}/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(slug: str, product: ProductCreate, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
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
    
    # Optional filtering by category query parameter
    if category:
        query = query.filter(DBProduct.category == category)
        
    return query.all()

@app.get("/stores/{slug}/categories")
def list_categories(slug: str, db: Session = Depends(get_db)):
    store = db.query(DBStore).filter(DBStore.slug == slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    # Query distinct categories available in store
    categories = db.query(DBProduct.category).filter(
        DBProduct.store_id == store.id, 
        DBProduct.in_stock == True
    ).distinct().all()
    
    return [c[0] for c in categories if c[0]]


# --- WHATSAPP CHECKOUT ENGINE ---
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