"""API routes and endpoints demonstrating async performance and pagination."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import Order, get_db
from .services import cache_get, cache_set, sanitize_comment

router = APIRouter(prefix="/api/v1", tags=["orders"])


class OrderCreateRequest(BaseModel):
    user_id: int
    amount: float = Field(gt=0.0)
    customer_notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: OrderCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new order asynchronously with sanitized inputs."""
    _notes = sanitize_comment(request.customer_notes) if request.customer_notes else ""
    order = Order(
        user_id=request.user_id,
        total_amount=request.amount,
        status="created" if not _notes else "reviewed",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
    )


@router.get("/orders", response_model=List[OrderResponse])
async def list_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """List orders with pagination (limit and offset) and caching."""
    cache_key = f"orders_list:l={limit}:o={offset}:s={status_filter}"
    cached = cache_get(cache_key)
    if cached is not None:
        return [OrderResponse(**item) for item in cached]

    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = query.offset(offset).limit(limit).all()
    results = [
        OrderResponse(
            id=o.id,
            user_id=o.user_id,
            total_amount=o.total_amount,
            status=o.status,
        )
        for o in orders
    ]
    cache_set(cache_key, [r.model_dump() for r in results], ttl=60)
    return results


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve single order by primary key."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_amount=order.total_amount,
        status=order.status,
    )
