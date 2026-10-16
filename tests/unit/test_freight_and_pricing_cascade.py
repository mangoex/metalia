"""
Pruebas unitarias para RN-10 (Matriz de Fletes Nacional), RN-11 (Cascada Comercial con Espuma FM)
y RN-12 (Trazabilidad Financiera y Alerta de Margen Mínimo) — Cubre HU-08 y HU-09.
"""

from decimal import Decimal

import pytest

from app.services.freight_service import calculate_destination_freight, get_freight_destination
from app.services.pricing_quote_service import calculate_commercial_cascade


def test_hu08_national_freight_lookup_and_exact_cost_culiacan():
    """Valida la consulta de flete nacional para Culiacán, Sinaloa y el costo exacto por ml en 1.5 pulgadas."""
    dest = get_freight_destination("Sinaloa", "Culiacán")
    assert dest is not None
    assert dest["estado"] == "Sinaloa"
    assert "Culiac" in dest["destino"]
    
    tarifa_15 = Decimal(str(dest["techos_ml"]['1.5"']))
    # Tarifa real de 1.5" para Culiacán, Sinaloa en Fletes 2023 es 77.5619 $/ml
    assert tarifa_15 == pytest.approx(Decimal("77.5619"), rel=Decimal("1e-3"))

    # 160 piezas de 6.33 m = 1,012.80 ml
    ml_total = Decimal(160) * Decimal("6.33")
    flete = calculate_destination_freight(
        estado="Sinaloa",
        municipio="Culiacán",
        tipo_aplicacion="TECHO",
        espesor_pulg='1.5"',
        longitud_total_ml=ml_total,
        peso_total_kg=Decimal("10654.40"),
    )
    # 1012.80 * 77.5619 = 78,554.69232 -> redondeado a 78,554.69
    assert flete["costo_flete_mxn"] == pytest.approx(Decimal("78554.69"), abs=Decimal("1.00"))
    assert flete["metodo_calculo"] == "TARIFA_POR_METRO_LINEAL"


def test_rn10_freight_by_weight_for_acanalados_and_accessories():
    """Valida que para acanalados simples o accesorios se use la tarifa por tonelada."""
    flete = calculate_destination_freight(
        estado="Aguascalientes",
        municipio="Aguascalientes",
        tipo_aplicacion="TECHO",
        espesor_pulg=None,
        longitud_total_ml=Decimal("0.0"),
        peso_total_kg=Decimal("5000.00"),
    )
    # 5,000 kg = 5.0 ton * $1,070/ton = $5,350.00 MXN
    assert flete["costo_flete_mxn"] == Decimal("5350.00")
    assert flete["metodo_calculo"] == "RECUPERACION_POR_TONELADA"


def test_hu09_commercial_pricing_cascade_with_fm_foam_option():
    """Valida la fórmula en cascada comercial con +7% de espuma Factory Mutual y margen de 25%."""
    resultado = calculate_commercial_cascade(
        precio_lista_base_m2=Decimal("706.82"),
        descuento_planta_pct=Decimal("0.34"),
        indirecto_pct=Decimal("0.00"),
        margen_utilidad_pct=Decimal("0.25"),
        es_espuma_fm=True,
        flete_unitario_m2=Decimal("46.23"),
    )

    # 1. Precio lista ajustado FM (+7%): 706.82 * 1.07 = 756.2974
    assert resultado["precio_lista_ajustado_m2"] == Decimal("756.30")
    # 2. Costo neto compra: 756.2974 * (1 - 0.34) = 499.1563 -> 499.16
    assert resultado["costo_neto_compra_m2"] == Decimal("499.16")
    # 3. Costo con indirecto (0%): 499.1563 -> 499.16
    assert resultado["costo_con_indirecto_m2"] == Decimal("499.16")
    # 4. Precio venta sin flete (+25%): 499.1563 * 1.25 = 623.9454 -> 623.95
    assert resultado["precio_venta_sin_flete_m2"] == Decimal("623.95")
    # 5. Utilidad bruta: 623.9454 - 499.1563 = 124.7891 -> 124.79
    assert resultado["utilidad_bruta_m2"] == Decimal("124.79")
    # 6. Margen sobre venta: 124.7891 / 623.9454 = 20.00%
    assert resultado["margen_bruto_pct"] == Decimal("20.00")
    # 7. Precio unitario final con flete: 623.95 + 46.23 = 670.18
    assert resultado["pu_final_con_flete_m2"] == Decimal("670.18")
    assert not resultado["alerta_margen_bajo"]


def test_rn12_low_margin_alert_below_15_percent():
    """Valida que un margen de utilidad menor al 15% sobre venta active la alerta institucional."""
    # margen_utilidad sobre costo del 10% genera un margen sobre venta de ~9.09% (< 15%)
    resultado = calculate_commercial_cascade(
        precio_lista_base_m2=Decimal("706.82"),
        descuento_planta_pct=Decimal("0.34"),
        indirecto_pct=Decimal("0.00"),
        margen_utilidad_pct=Decimal("0.10"),
        es_espuma_fm=False,
        flete_unitario_m2=Decimal("0.00"),
    )
    assert resultado["alerta_margen_bajo"]
    assert resultado["margen_bruto_pct"] < Decimal("15.00")
