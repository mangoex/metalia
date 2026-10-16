"""Pruebas unitarias para Vigencia de Cotización (72h), Reserva por Anticipo 50% e Instalación (HU-04, HU-06)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest


def test_hu04_turnkey_installation_and_freight_quote(store):
    """
    HU-04: Cuando el usuario activa 'Incluir Instalación Metalia' e ingresa el CP de su obra
    en Querétaro, el sistema añade mano de obra de instalación por m2 y calcula el flete.
    """
    from app.models.domain import CreateNaveQuoteRequest
    from app.services.pricing_quote_service import create_nave_quote

    req = CreateNaveQuoteRequest(
        cliente_nombre="Ing. Roberto Méndez",
        cliente_empresa="Constructora Bajío Industrial S.A. de C.V.",
        cliente_whatsapp="4421234567",
        cliente_email="rmendez@constructorabajio.mx",
        largo_nave_m=Decimal("40.0"),
        ancho_nave_m=Decimal("25.0"),
        altura_muro_m=Decimal("6.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("5.0"),
        area_huecos_m2=Decimal("20.0"),
        alcance_obra="NAVE_COMPLETA",
        sku_cubierta="GALVATECHO-15-2626-ARENA",
        sku_muro="MULTYMURO-15-2626-ARENA",
        incluir_bom_accesorios=True,
        incluir_estructura_polin=True,
        incluir_instalacion=True,
        codigo_postal_obra="76220",
        tipo_entrega="FLETE_OBRA",
    )

    quote = create_nave_quote(req, store)

    subsistemas = {p.subsistema for p in quote.partidas}
    assert "CUBIERTA" in subsistemas
    assert "MURO" in subsistemas
    assert "INSTALACION" in subsistemas
    assert "FLETE" in subsistemas
    assert quote.anticipo_50_mxn == (quote.total_mxn * Decimal("0.50")).quantize(Decimal("0.01"))


def test_hu06_quote_expiration_after_72_business_hours_and_recalculation(store):
    """
    HU-06 (Criterio Gherkin Exacto):
    Dado que una cotización fue emitida hace más de 72 horas hábiles,
    Cuando el cliente consulta la cotización o intenta pagar al precio histórico,
    Entonces:
    - Muestra 'Cotización Expirada por Vigencia de Precios del Acero' (estado EXPIRADA)
    - Bloquea el pago de anticipo sin recálculo
    - Permite recalcular las partidas al nuevo precio del acero y stock del día
    """
    from app.models.domain import CreateDirectQuoteRequest, DirectLineInput
    from app.services.pricing_quote_service import (
        check_and_update_quote_validity,
        create_direct_quote,
        mass_update_steel_prices,
        recalculate_expired_quote,
        register_advance_payment,
    )

    emitted_at = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)  # Lunes
    req = CreateDirectQuoteRequest(
        cliente_nombre="Arq. Sofía Vega",
        cliente_empresa="Desarrollos QRO",
        cliente_whatsapp="4429876543",
        cliente_email="svega@desarrollosqro.mx",
        lineas=[
            DirectLineInput(
                sku="MULTYMURO-15-2626-ARENA",
                cantidad_piezas=20,
                largo_pieza_m=Decimal("6.00"),
            )
        ],
        fecha_emision_override=emitted_at,
    )
    quote = create_direct_quote(req, store)
    original_total = quote.total_mxn

    # 5 días después (> 72 horas hábiles)
    now_expired = emitted_at + timedelta(days=5)
    validity = check_and_update_quote_validity(quote, current_time=now_expired)

    assert validity.estado == "EXPIRADA"
    assert "Cotización Expirada por Vigencia de Precios del Acero" in validity.mensaje_vigencia

    # Intentar pagar anticipo sobre cotización expirada debe fallar
    with pytest.raises(ValueError, match="Cotización Expirada"):
        register_advance_payment(quote.folio, store, current_time=now_expired)

    # Sube el precio del acero un 8%
    mass_update_steel_prices(store, porcentaje_ajuste=Decimal("8.0"))

    # Recalcular cotización al precio del día
    refreshed = recalculate_expired_quote(quote.folio, store, current_time=now_expired)
    assert refreshed.estado == "ENVIADA"
    assert refreshed.total_mxn > original_total


def test_advance_payment_50_percent_reserves_dimensional_stock(store):
    """Verifica que el pago del 50% de anticipo reserve las piezas en Inventario_Dimensional_Piso."""
    from app.models.domain import CreateDirectQuoteRequest, DirectLineInput
    from app.services.pricing_quote_service import create_direct_quote, register_advance_payment

    lote = store.find_lot("MULTYMURO-15-2626-ARENA", Decimal("6.00"))
    disp_before = lote.cantidad_piezas_disponibles
    res_before = lote.cantidad_piezas_reservadas

    req = CreateDirectQuoteRequest(
        cliente_nombre="Ing. Carlos Ruiz",
        cliente_empresa="Estructuras del Centro",
        cliente_whatsapp="4425551122",
        cliente_email="cruiz@estructuras.mx",
        lineas=[
            DirectLineInput(
                sku="MULTYMURO-15-2626-ARENA",
                cantidad_piezas=10,
                largo_pieza_m=Decimal("6.00"),
            )
        ],
    )
    quote = create_direct_quote(req, store)
    updated_quote = register_advance_payment(quote.folio, store)

    assert updated_quote.estado == "ANTICIPO_50_PAGADO"
    assert lote.cantidad_piezas_disponibles == disp_before - 10
    assert lote.cantidad_piezas_reservadas == res_before + 10
