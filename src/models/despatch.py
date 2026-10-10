from datetime import datetime, date
from src.core.datetime_peru import now_peru
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Despatch(Base):
    __tablename__ = "despatches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    is_test_mode = Column(Boolean, default=False, nullable=False, index=True)

    facturador_despatch_id = Column(String(36), nullable=True, index=True)
    external_id = Column(String(100), nullable=True, index=True)

    # 09 = Guía Remitente, 31 = Guía Transportista
    type_code = Column(String(2), default="09", nullable=False, index=True)
    series = Column(String(4), nullable=False, index=True)
    correlative = Column(Integer, nullable=False, index=True)

    issue_date = Column(Date, default=date.today, nullable=False, index=True)
    issue_time = Column(String(8), default="12:00:00", nullable=False)
    transfer_date = Column(Date, default=date.today, nullable=False)
    delivery_date = Column(Date, nullable=True)

    # 01 = Público, 02 = Privado
    transport_mode = Column(String(2), default="01", nullable=False)
    # 01 = Venta, 04 = Traslado entre establecimientos, 13 = Otros, etc.
    transfer_reason = Column(String(5), default="01", nullable=False)
    transfer_description = Column(String(255), nullable=True)

    total_weight = Column(Numeric(14, 4), nullable=False)
    weight_unit = Column(String(5), default="TNE", nullable=False) # TNE o KGM
    packages_count = Column(Integer, default=1, nullable=False)

    # Destinatario
    recipient = Column(JSON, nullable=False) # {doc_type, doc_number, name, address, email}

    # Puntos de partida y llegada
    origin = Column(JSON, nullable=False) # {ubigeo, address}
    destination = Column(JSON, nullable=False) # {ubigeo, address}

    # Transporte público
    carrier = Column(JSON, nullable=True) # {doc_type, doc_number, name, mtc}

    # Transporte privado
    driver = Column(JSON, nullable=True) # {doc_type, doc_number, name, license}
    vehicle = Column(JSON, nullable=True) # {plate, secondary_plate} (contrato Factos)

    # Estado SUNAT / Factos: pending, accepted, rejected, voided
    status = Column(String(20), default="pending", nullable=False, index=True)
    sunat_code = Column(String(10), nullable=True)
    sunat_description = Column(Text, nullable=True)
    sunat_notes = Column(JSON, nullable=True)

    # Archivos
    pdf_url = Column(String(500), nullable=True)
    xml_url = Column(String(500), nullable=True)
    cdr_url = Column(String(500), nullable=True)
    void_reason = Column(String(255), nullable=True)
    voided_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=now_peru, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="despatches")
    items = relationship("DespatchItem", back_populates="despatch", cascade="all, delete-orphan")

    @property
    def despatch_number(self) -> str:
        return f"{self.series}-{str(self.correlative).zfill(8)}"

class DespatchItem(Base):
    __tablename__ = "despatch_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    despatch_id = Column(Integer, ForeignKey("despatches.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_code = Column(String(50), nullable=True)
    description = Column(String(500), nullable=False)
    unit_code = Column(String(5), default="TNE", nullable=False)
    quantity = Column(Numeric(14, 4), default=1.0000, nullable=False)

    despatch = relationship("Despatch", back_populates="items")
