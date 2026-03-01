from __future__ import annotations

from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.product import ProductCreate, ProductRead
from src.core.database import get_db
from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.repositories.product_repository import ProductRepository


router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=List[ProductRead], status_code=status.HTTP_201_CREATED)
async def add_products(
    items: Sequence[ProductCreate],
    db: AsyncSession = Depends(get_db),
) -> List[ProductRead]:
    repo = ProductRepository(db)
    created: list[Product] = []
    for item in items:
        if await db.get(Batch, item.batch_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch {item.batch_id} not found",
            )
        created.append(await repo.create(item.model_dump()))
    await db.commit()
    return created



