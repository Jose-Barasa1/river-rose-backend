from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.get("/", response_model=List[schemas.ReviewOut])
def get_reviews(product_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Public — get all reviews or filter by ?product_id=1"""
    query = db.query(models.Review)
    if product_id:
        query = query.filter(models.Review.product_id == product_id)
    return query.order_by(models.Review.created_at.desc()).all()


@router.post("/", response_model=schemas.ReviewOut)
def create_review(review: schemas.ReviewCreate, db: Session = Depends(get_db)):
    """Public — anyone can leave a review (no login required)."""
    if not 1 <= review.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")
    db_review = models.Review(
        name=review.name,
        comment=review.comment,
        rating=review.rating,
        product_id=review.product_id,
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review