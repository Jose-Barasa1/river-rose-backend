from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import CommunityPost
from app.schemas import CommunityPostCreate, CommunityPostOut

router = APIRouter()

@router.get("/", response_model=List[CommunityPostOut])
def get_posts(db: Session = Depends(get_db)):
    return db.query(CommunityPost).order_by(CommunityPost.created_at.desc()).all()

@router.post("/", response_model=CommunityPostOut)
def create_post(post: CommunityPostCreate, db: Session = Depends(get_db)):
    new_post = CommunityPost(**post.dict())
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post

@router.patch("/{post_id}/like", response_model=CommunityPostOut)
def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.likes += 1
    db.commit()
    db.refresh(post)
    return post