"""
Punto de entrada FastAPI para el Sistema Web CPQ, Explosión de Materiales (BOM),
Inventario Dimensional en Piso y Pre-Validador Carta Porte 3.1 de Metalia (Querétaro).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.models.domain import create_default_metalia_store

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "web" / "templates"
STATIC_DIR = BASE_DIR / "web" / "static"


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI con estado inicializado de Metalia Querétaro."""
    app = FastAPI(
        title="Metalia CPQ & Inventario Dimensional API",
        description=(
            "Sistema Configurador de Productos, Precios y Cotizaciones (CPQ), Explosión BOM, "
            "Control de Inventario por Largos en Piso y Pre-Validador Carta Porte 3.1 para Metalia Querétaro."
        ),
        version="1.0.0",
    )

    app.state.store = create_default_metalia_store()
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    app.include_router(api_router)

    @app.get("/", response_class=HTMLResponse)
    def render_portal(request: Request):
        store = request.app.state.store
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "familias": list(store.familias.values()),
                "variantes": list(store.variantes.values()),
                "inventario_piso": store.inventario_piso,
            },
        )

    return app


app = create_app()
