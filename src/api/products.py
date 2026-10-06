from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.product import Product
from src.schemas.product import ProductCreate, ProductOut

router = APIRouter(prefix="/products", tags=["Catálogo de Productos y Servicios"])

@router.get("", response_model=List[ProductOut])
def list_products(
    company_id: Optional[int] = Query(None),
    query: Optional[str] = Query(None),
    include_inactive: bool = Query(False, description="Incluir productos eliminados lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product)
    if not include_inactive:
        q = q.filter(Product.is_active == True)
    if company_id:
        q = q.filter(Product.company_id == company_id)
    if query:
        pattern = f"%{query}%"
        q = q.filter((Product.description.ilike(pattern)) | (Product.internal_code.ilike(pattern)))
    return q.order_by(Product.id.asc()).all()

@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = Product(
        company_id=payload.company_id,
        internal_code=payload.internal_code,
        description=payload.description,
        unit_code=payload.unit_code,
        unit_value=payload.unit_value,
        unit_price=payload.unit_price,
        igv_type=payload.igv_type,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de producto. Nunca se elimina físicamente de la base de datos."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if not product.is_active:
        return {"message": "El producto ya se encuentra inactivo", "id": product_id, "is_active": False}

    product.is_active = False
    product.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Producto eliminado lógicamente con éxito", "id": product_id, "is_active": False}
