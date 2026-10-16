"""
Pruebas unitarias para RN-13 (Acanalados Simples y Losacero), RN-14 (Translúcidos Stabilit Acrylit G10)
y RN-15 (Molduras WizERP con desarrollo desplegado) — Cubre HU-10 y HU-11.
"""

from decimal import Decimal

import pytest

from app.models.domain import (
    NaveGeometryInput,
    create_default_metalia_store,
)
from app.services.bom_engine import generate_bom_for_nave
from app.services.geometry_engine import calculate_nave_geometry


def test_hu10_nave_with_acrylit_translucent_daylight_strips():
    """Valida la sustitución de hileras opacas por translúcidas Acrylit G10 manteniendo modulación geométrica."""
    store = create_default_metalia_store()
    inp = NaveGeometryInput(
        largo_nave_m=Decimal("40.0"),
        ancho_nave_m=Decimal("25.0"),
        altura_muro_m=Decimal("0.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("5.0"),
        sku_cubierta="GALVATECHO-26-28-15-PIN",
        porcentaje_luz_natural_pct=Decimal("10.0"),  # 10% de franjas de luz
    )
    geo = calculate_nave_geometry(inp, store)
    # Total hileras = 40 (por agua: 40 hileras, repartidas en 2 aguas = 80 medios faldones)
    # 10% de luz natural -> 4 hileras translúcidas de Acrylit G10
    assert geo.hileras_luz_natural == 4
    assert geo.hileras_opacas == 36
    assert geo.area_luz_natural_m2 > Decimal(0)

    bom = generate_bom_for_nave(inp, geo, store)
    # Debe existir partida de cubierta opaca y partida de translúcido
    skus_bom = [item.sku for item in bom.partidas]
    assert "GALVATECHO-26-28-15-PIN" in skus_bom
    assert any("ACRYLIT" in sku or "POLIACRYL" in sku for sku in skus_bom)

    # El BOM debe incluir cinta de butilo y sellador PU reforzados para los empalmes de acrílico
    assert any("BUTILO" in sku for sku in skus_bom)
    assert any("SELLADOR" in sku for sku in skus_bom)


def test_hu11_losacero_and_wizerp_molduras():
    """Valida especificaciones de Losacero 25 y molduras de taller con código WizERP y desarrollo en cm."""
    store = create_default_metalia_store()

    # 1. Losacero 25
    assert "LOSACERO_25" in store.familias
    fam_losa = store.familias["LOSACERO_25"]
    assert fam_losa.ancho_efectivo_m == pytest.approx(Decimal("0.9144"), rel=Decimal("1e-4"))
    assert fam_losa.mecanismo_fijacion == "EXPUESTA_TRASLAPE"

    # 2. Molduras WizERP
    molduras = store.molduras_wizerp
    assert len(molduras) >= 4
    
    canal_15 = next((m for m in molduras if m.codigo_wizerp == "CIIPFC2215305152"), None)
    assert canal_15 is not None
    assert canal_15.desarrollo_cm == Decimal("15.1")
    assert canal_15.tiras_por_lamina == 8  # 122 / 15.1 = 8
    assert canal_15.costo_maquila_pza == Decimal("55.00")
    # Costo lámina por tira = 756.06 / 8 = 94.5075
    # Costo habilitado = 94.5075 + 55.00 = 149.5075 -> ~149.51
    assert canal_15.costo_unitario_habilitado == pytest.approx(Decimal("149.51"), abs=Decimal("0.10"))
