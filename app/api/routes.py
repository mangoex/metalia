"""
Endpoints RESTful para el Catálogo Técnico, Motor CPQ Dual, Inventario Dimensional en Piso,
Órdenes de Corte / Retazos y Pre-Validador de Complemento Carta Porte 3.1.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.domain import (
    CartaPorteMercanciaInput,
    CartaPorteRequest,
    CreateDirectQuoteRequest,
    CreateNaveQuoteRequest,
    MetaliaInMemoryStore,
    NaveGeometryInput,
)
from app.services.bom_engine import generate_bom_for_nave
from app.services.geometry_engine import calculate_nave_geometry
from app.services.inventory_service import (
    evaluate_direct_line_stock,
    execute_cut_order,
)
from app.services.logistics_carta_porte import build_and_validate_carta_porte_31
from app.services.pricing_quote_service import (
    check_and_update_quote_validity,
    create_direct_quote,
    create_nave_quote,
    mass_update_steel_prices,
    recalculate_expired_quote,
    register_advance_payment,
)

router = APIRouter(prefix="/api/v1", tags=["Metalia CPQ API"])


class CutOrderExecuteInput(BaseModel):
    id_lote_origen: str
    cantidad_piezas: int = Field(gt=0)
    largo_corte_m: Decimal = Field(gt=Decimal(0))


class SteelPriceUpdateInput(BaseModel):
    porcentaje_ajuste: Decimal


class QuoteCartaPorteInput(BaseModel):
    modalidad_transporte: Literal["FLOTA_PROPIA_TRASLADO", "FLETERA_TERCERO_INGRESO"] = (
        "FLOTA_PROPIA_TRASLADO"
    )
    permiso_sct: str = "TPAF01"
    numero_permiso_sct: str = "SCT-QRO-2026-8842"
    config_vehicular: str = "T3S2"
    placa_vm: str = "QRO901X"
    anio_modelo_vm: int = 2025
    subtipo_remolque: str | None = "CTR021"
    placa_remolque: str | None = "99RM1A"
    operador_nombre: str = "Operador Metalia Querétaro"
    operador_rfc: str = "TOMA820512QRO"
    operador_licencia: str = "FED776655"
    monto_flete_mxn: Decimal = Decimal("0.00")


def _get_store(request: Request) -> MetaliaInMemoryStore:
    return request.app.state.store


@router.get("/catalog")
def get_catalog_and_inventory(request: Request):
    """Retorna el catálogo técnico paramétrico y la matriz de existencias en piso en Querétaro."""
    store = _get_store(request)
    return {
        "familias": list(store.familias.values()),
        "variantes": list(store.variantes.values()),
        "inventario_piso": store.inventario_piso,
        "ordenes_corte": store.ordenes_corte,
    }


@router.post("/cpq/preview-nave")
def preview_nave_geometry_and_bom(inp: NaveGeometryInput, request: Request):
    """Calcula en tiempo real la geometría de la nave (RN-01..RN-04) y la explosión BOM (RN-06..RN-08)."""
    store = _get_store(request)
    try:
        geo = calculate_nave_geometry(inp, store)
        bom = generate_bom_for_nave(inp, geo, store)
        return {"geometria": geo, "bom": bom}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cpq/evaluate-stock")
def evaluate_stock_line(
    sku: str,
    cantidad_piezas: int,
    largo_requerido_m: Decimal,
    request: Request,
):
    """Verifica disponibilidad en piso en Querétaro, corte de hoja maestra o pedido a planta (RN-05)."""
    store = _get_store(request)
    try:
        return evaluate_direct_line_stock(store, sku, cantidad_piezas, largo_requerido_m)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quotes/direct")
def api_create_direct_quote(req: CreateDirectQuoteRequest, request: Request):
    """Genera una cotización formal CPQ en Modo Directo por Despiece (HU-02)."""
    store = _get_store(request)
    try:
        return create_direct_quote(req, store)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quotes/nave")
def api_create_nave_quote(req: CreateNaveQuoteRequest, request: Request):
    """Genera una cotización formal CPQ en Modo Proyecto / Nave Industrial (HU-01, HU-03, HU-04)."""
    store = _get_store(request)
    try:
        return create_nave_quote(req, store)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quotes/{folio}")
def api_get_quote(folio: str, request: Request):
    """Consulta una cotización por su folio verificando su vigencia de 72h hábiles (HU-06)."""
    store = _get_store(request)
    if folio not in store.cotizaciones:
        raise HTTPException(status_code=404, detail=f"Folio {folio} no encontrado")
    quote = store.cotizaciones[folio]
    return check_and_update_quote_validity(quote)


@router.post("/quotes/{folio}/advance-payment")
def api_register_advance_payment(folio: str, request: Request):
    """Registra el anticipo del 50% y reserva los lotes en piso en Querétaro."""
    store = _get_store(request)
    try:
        return register_advance_payment(folio, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quotes/{folio}/recalculate")
def api_recalculate_quote(folio: str, request: Request):
    """Recalcula una cotización expirada al precio del acero y stock del día (HU-06)."""
    store = _get_store(request)
    try:
        return recalculate_expired_quote(folio, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quotes/{folio}/carta-porte")
def api_generate_carta_porte_from_quote(
    folio: str,
    inp: QuoteCartaPorteInput,
    request: Request,
):
    """
    Genera y pre-valida el payload JSON del Complemento Carta Porte 3.1 (SAT)
    a partir de las mercancías físicas de una cotización (HU-07, RN-09).
    """
    store = _get_store(request)
    if folio not in store.cotizaciones:
        raise HTTPException(status_code=404, detail=f"Folio {folio} no encontrado")
    quote = store.cotizaciones[folio]

    mercancias = [
        CartaPorteMercanciaInput(
            bienes_transp_sat=p.clave_prod_serv_sat,
            descripcion=p.descripcion,
            cantidad=Decimal(p.cantidad_piezas),
            clave_unidad_sat=p.clave_unidad_sat,
            peso_en_kg=p.peso_partida_kg,
            largo_m=p.largo_facturado_m,
        )
        for p in quote.partidas
        if p.es_mercancia_fisica and p.peso_partida_kg > Decimal(0)
    ]

    cp_req = CartaPorteRequest(
        folio_cotizacion=quote.folio,
        modalidad_transporte=inp.modalidad_transporte,
        codigo_postal_origen="76000",
        codigo_postal_destino=quote.codigo_postal_obra,
        permiso_sct=inp.permiso_sct,
        numero_permiso_sct=inp.numero_permiso_sct,
        config_vehicular=inp.config_vehicular,
        placa_vm=inp.placa_vm,
        anio_modelo_vm=inp.anio_modelo_vm,
        subtipo_remolque=inp.subtipo_remolque,
        placa_remolque=inp.placa_remolque,
        operador_nombre=inp.operador_nombre,
        operador_rfc=inp.operador_rfc,
        operador_licencia=inp.operador_licencia,
        monto_flete_mxn=inp.monto_flete_mxn,
        peso_bruto_total_declarado_kg=quote.peso_bruto_total_kg,
        mercancias=mercancias,
    )
    try:
        payload = build_and_validate_carta_porte_31(cp_req)
        quote.estado = "CARTA_PORTE_TIMBRADA"
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/inventory/cut-orders")
def api_execute_cut_order(inp: CutOrderExecuteInput, request: Request):
    """Ejecuta una orden de corte sobre hoja maestra y da de alta retazos si sobrante >= 2.00 m (HU-05)."""
    store = _get_store(request)
    try:
        return execute_cut_order(
            store=store,
            id_lote_origen=inp.id_lote_origen,
            cantidad_piezas=inp.cantidad_piezas,
            largo_corte_m=inp.largo_corte_m,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/steel-price-adjustment")
def api_mass_update_steel_prices(inp: SteelPriceUpdateInput, request: Request):
    """Actualiza masivamente los precios base del acero por m² (HU-06)."""
    store = _get_store(request)
    updated = mass_update_steel_prices(store, inp.porcentaje_ajuste)
    return {
        "variantes_actualizadas": updated,
        "porcentaje_aplicado": str(inp.porcentaje_ajuste),
        "variantes": list(store.variantes.values()),
    }
