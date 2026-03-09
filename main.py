from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, products, orders, reviews

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="River Rose API", version="2.0.0")

# CORS — add your Vercel URL here
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://river-rose.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(orders.router,   prefix="/api/orders",   tags=["Orders"])
app.include_router(reviews.router,  prefix="/api/reviews",  tags=["Reviews"])

@app.get("/")
def root():
    return {"message": "River Rose API is running 🌸"}