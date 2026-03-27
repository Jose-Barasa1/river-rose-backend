from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, init_db
from app.routers import auth, products, orders, reviews, mpesa, community, admin

# Create all tables
Base.metadata.create_all(bind=engine)

# Initialize database with default admin
init_db()

app = FastAPI(title="River Rose API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://river-rose.vercel.app",
        "https://river-rose-git-main-jose-barasa1s-projects.vercel.app",
        "https://river-rose-42b8iwo2p-jose-barasa1s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(products.router,  prefix="/api/products",  tags=["Products"])
app.include_router(orders.router,    prefix="/api/orders",    tags=["Orders"])
app.include_router(reviews.router,   prefix="/api/reviews",   tags=["Reviews"])
app.include_router(mpesa.router,     prefix="/api/mpesa",     tags=["Mpesa"])
app.include_router(community.router, prefix="/api/community", tags=["Community"])
app.include_router(admin.router,     prefix="/api/admin",     tags=["Admin"])

@app.get("/")
def root():
    return {"message": "River Rose API is running 🌸"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
