from pydantic import BaseModel

class ProductBase(BaseModel):
    name: str
    price: float
    description: str | None = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True
