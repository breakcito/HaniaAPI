from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(prefix="/products", tags=["Catálogo de Productos y Servicios"])

@router.get("", response_model=List[ProductOut])
def list_products(
    query: Optional[str] = Query(None, description="Búsqueda por descripción o código SUNAT"),
    is_service: Optional[bool] = Query(None, description="Filtrar servicios vs bienes"),
    include_inactive: bool = Query(False, description="Incluir productos eliminados lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product)
    if not include_inactive:
        q = q.filter(Product.is_active == True)
    if is_service is not None:
        q = q.filter(Product.is_service == is_service)
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            (Product.description.ilike(pattern))
            | (Product.sunat_code.ilike(pattern))
        )
    return q.order_by(Product.description.asc()).all()

@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = Product(
        sunat_code=payload.sunat_code.strip() if payload.sunat_code else None,
        description=payload.description.strip(),
        unit_code=payload.unit_code,
        currency=payload.currency or "PEN",
        unit_value=payload.unit_value if payload.unit_value is not None else (round(payload.unit_price / Decimal("1.18"), 4) if payload.unit_price else Decimal("0.00")),
        unit_price=payload.unit_price,
        igv_type=payload.igv_type,
        has_detraction=payload.has_detraction,
        detraction_code=payload.detraction_code,
        detraction_percent=payload.detraction_percent,
        is_service=payload.is_service,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(product, k, v)

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de producto."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if not product.is_active:
        return {"message": "El producto ya se encuentra inactivo", "id": product_id, "is_active": False}

    product.is_active = False
    product.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Producto eliminado lógicamente con éxito", "id": product_id, "is_active": False}
