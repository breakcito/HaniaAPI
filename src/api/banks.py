from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.bank import Bank, BankAccount
from src.schemas.bank import BankOut, BankAccountCreate, BankAccountUpdate, BankAccountOut

router = APIRouter(tags=["Bancos y Cuentas Bancarias"])

# ==========================================
# Catálogo de Bancos
# ==========================================
@router.get("/banks", response_model=List[BankOut])
def list_banks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las entidades bancarias y financieras habilitadas en el sistema."""
    return db.query(Bank).filter(Bank.is_active == True).order_by(Bank.name.asc()).all()


# ==========================================
# Cuentas Bancarias Empresariales
# ==========================================
@router.get("/bank-accounts", response_model=List[BankAccountOut])
def list_bank_accounts(
    company_id: Optional[int] = Query(None, description="Filtrar por empresa"),
    account_type: Optional[str] = Query(None, description="corriente, ahorros, detraccion"),
    currency: Optional[str] = Query(None, description="PEN, USD"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las cuentas bancarias de la empresa (detracciones, cuentas corrientes, etc.)."""
    q = db.query(BankAccount)
    if not include_inactive:
        q = q.filter(BankAccount.is_active == True)
    if company_id is not None:
        q = q.filter(BankAccount.company_id == company_id)
    if account_type:
        q = q.filter(BankAccount.account_type == account_type)
    if currency:
        q = q.filter(BankAccount.currency == currency.upper())

    return q.order_by(BankAccount.is_default.desc(), BankAccount.id.asc()).all()


@router.post("/bank-accounts", response_model=BankAccountOut, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra una nueva cuenta bancaria para la empresa."""
    company = db.query(Company).filter(Company.id == payload.company_id, Company.is_active == True).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    bank = db.query(Bank).filter(Bank.id == payload.bank_id, Bank.is_active == True).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Entidad bancaria no válida")

    # Si es cuenta por defecto, desmarcar otras cuentas de la misma moneda y tipo
    if payload.is_default:
        db.query(BankAccount).filter(
            BankAccount.company_id == payload.company_id,
            BankAccount.currency == payload.currency,
            BankAccount.account_type == payload.account_type,
        ).update({"is_default": False})

    new_account = BankAccount(
        company_id=payload.company_id,
        bank_id=payload.bank_id,
        account_type=payload.account_type,
        currency=payload.currency.upper(),
        account_number=payload.account_number.strip(),
        cci_number=payload.cci_number.strip() if payload.cci_number else None,
        alias=payload.alias.strip() if payload.alias else None,
        show_in_pdf=payload.show_in_pdf,
        is_default=payload.is_default,
        is_active=True,
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


@router.put("/bank-accounts/{account_id}", response_model=BankAccountOut)
def update_bank_account(
    account_id: int,
    payload: BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza la información de una cuenta bancaria empresarial."""
    account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    if "is_default" in update_data and update_data["is_default"]:
        db.query(BankAccount).filter(
            BankAccount.company_id == account.company_id,
            BankAccount.currency == (payload.currency or account.currency),
            BankAccount.account_type == (payload.account_type or account.account_type),
            BankAccount.id != account.id,
        ).update({"is_default": False})

    for key, value in update_data.items():
        setattr(account, key, value)

    account.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/bank-accounts/{account_id}")
def delete_bank_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación lógica de una cuenta bancaria."""
    account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada")

    account.is_active = False
    account.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Cuenta bancaria eliminada lógicamente con éxito", "id": account_id}
