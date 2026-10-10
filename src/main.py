import sys
from pathlib import Path

# Asegurar que el directorio raíz del proyecto esté siempre en sys.path
# Compatible con `fastapi dev src/main.py`, `fastapi run`, `uvicorn`, etc.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from src.core.config import settings
from src.services.init_db import init_db
from src.api.auth import router as auth_router
from src.api.companies import router as companies_router
from src.api.documents import router as documents_router
from src.api.despatches import router as despatches_router
from src.api.services import router as services_router
from src.api.clients import router as clients_router
from src.api.products import router as products_router
from src.api.dashboard import router as dashboard_router
from src.api.banks import router as banks_router
from src.api.series import router as series_router
from src.api.catalogs import router as catalogs_router
from src.api.webhooks import router as webhooks_router
from src.api.reports import router as reports_router
from src.api.employees import router as employees_router
from src.api.vehicles import router as vehicles_router
logger = logging.getLogger("hania_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando aplicación Hania API y sincronizando esquema de base de datos...")
    try:
        init_db()
        logger.info("Base de datos inicializada y sembrada con éxito.")
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
    yield
    logger.info("Finalizando Hania API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API empresarial para Corporación de Servicios Cupper & Hannia E.I.R.L - Sistema Multiempresa y Facturador SUNAT",
    lifespan=lifespan,
)

# Configuración de CORS para permitir solicitudes desde el frontend Vite (puerto 5173 / localhost / producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas bajo el prefijo /api
app.include_router(auth_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(despatches_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(banks_router, prefix="/api")
app.include_router(series_router, prefix="/api")
app.include_router(catalogs_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(employees_router, prefix="/api")
app.include_router(vehicles_router, prefix="/api")

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "company": settings.DEFAULT_COMPANY_NAME,
        "ruc": settings.DEFAULT_COMPANY_RUC,
    }
