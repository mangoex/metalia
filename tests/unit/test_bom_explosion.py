"""Pruebas unitarias para el Motor de Explosión de Materiales BOM (RN-06, RN-07, RN-08 y HU-03)."""

from decimal import Decimal


def test_hu03_bom_galvatecho_2_inch_screw_selection_and_clips(store):
    """
    HU-03 (Criterio Gherkin Exacto):
    Dado un cálculo de cubierta con panel Galvatecho de 2.0'' de espesor,
    Cuando se genera la explosión de materiales (BOM),
    Entonces:
    - Selecciona pijas autotaladrantes de 1/4'' x 4 3/4'' (regla espesor + 2.5'')
    - Asigna clips de fijación Galvatecho calibre 18 (47x38 mm)
    - No incluye tapajuntas (exclusivo de Multytecho)
    - Calcula caballetes y canalones en tramos de 3.05 m (rendimiento efectivo 2.90 m)
    - Incluye bajadas pluviales (1 cada 12.00 m de alero)
    """
    from app.models.domain import NaveGeometryInput
    from app.services.bom_engine import generate_bom_for_nave
    from app.services.geometry_engine import calculate_nave_geometry

    inp = NaveGeometryInput(
        largo_nave_m=Decimal("30.0"),
        ancho_nave_m=Decimal("16.0"),
        altura_muro_m=Decimal("5.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("10.0"),
        area_huecos_m2=Decimal("15.0"),
        alcance_obra="NAVE_COMPLETA",
        sku_cubierta="GALVATECHO-20-2626-ARENA",
        sku_muro="MULTYMURO-20-2626-ARENA",
    )

    geo = calculate_nave_geometry(inp, store)
    bom = generate_bom_for_nave(inp, geo, store)

    by_role = {item.tipo_regla: item for item in bom.items}

    # Pija principal para 2.0'' -> 1/4'' x 4 3/4''
    assert "PIJA_PRINCIPAL" in by_role
    assert "4 3/4" in by_role["PIJA_PRINCIPAL"].descripcion

    # Clip Galvatecho Cal. 18 presente
    assert "CLIP_FIJACION" in by_role
    assert by_role["CLIP_FIJACION"].cantidad > 0
    assert "Cal. 18" in by_role["CLIP_FIJACION"].descripcion

    # Sin tapajunta en Galvatecho
    assert "TAPAJUNTA" not in by_role or by_role["TAPAJUNTA"].cantidad == 0

    # Caballete central: ceil(30.0 / 2.90) = 11 piezas de 3.05 m
    assert by_role["CABALLETE"].cantidad == 11
    assert by_role["CABALLETE"].largo_pieza_m == Decimal("3.05")

    # Canalón en 2 aleros: ceil((2 * 30.0) / 2.90) = 21 piezas de 3.05 m
    assert by_role["CANALON"].cantidad == 21

    # Bajadas pluviales: ceil((2 * 30.0) / 12.00) = 5 piezas
    assert by_role["BAJADA_PLUVIAL"].cantidad == 5

    # Subsistema de muros incluido (Canal U base y Esquineros)
    assert "CANAL_U_BASE" in by_role
    assert "ESQUINERO" in by_role


def test_rn07_multytecho_includes_exact_tapajuntas_count(store):
    """
    RN-07: En Multytecho (fijación oculta), el BOM debe incluir obligatoriamente
    Piezas de Tapajunta = N_aguas * k * (N_hileras - 1) del mismo largo L_tramo.
    """
    from app.models.domain import NaveGeometryInput
    from app.services.bom_engine import generate_bom_for_nave
    from app.services.geometry_engine import calculate_nave_geometry

    # L=20m (20 hileras), W=16m (2 aguas -> 8m vertiente -> k=1 tramo)
    # Tapajuntas esperados = 2 * 1 * (20 - 1) = 38 piezas
    inp = NaveGeometryInput(
        largo_nave_m=Decimal("20.0"),
        ancho_nave_m=Decimal("16.0"),
        altura_muro_m=Decimal("0.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("5.0"),
        area_huecos_m2=Decimal("0.0"),
        alcance_obra="SOLO_TECHO",
        sku_cubierta="MULTYTECHO-15-2626-BLANCO",
    )

    geo = calculate_nave_geometry(inp, store)
    bom = generate_bom_for_nave(inp, geo, store)
    by_role = {item.tipo_regla: item for item in bom.items}

    assert "TAPAJUNTA" in by_role
    assert by_role["TAPAJUNTA"].cantidad == 38
    assert by_role["TAPAJUNTA"].largo_pieza_m == geo.largo_tramo_cortado_m


def test_rn06_screw_selector_across_all_panel_thicknesses():
    """RN-06: Verifica el mapeo de longitud de pija (espesor + 2.5'') para todos los rangos del catálogo."""
    from app.services.bom_engine import select_primary_screw_spec

    sku_lam, _, _, _ = select_primary_screw_spec(None)
    assert sku_lam == "PIJA-HEX-14-100"

    sku_10, _, _, _ = select_primary_screw_spec(Decimal("1.0"))
    assert sku_10 == "PIJA-HEX-14-350"

    sku_15, _, _, _ = select_primary_screw_spec(Decimal("1.5"))
    assert sku_15 == "PIJA-HEX-14-400"

    sku_20, _, _, _ = select_primary_screw_spec(Decimal("2.0"))
    assert sku_20 == "PIJA-HEX-14-475"

    sku_25, _, _, _ = select_primary_screw_spec(Decimal("2.5"))
    assert sku_25 == "PIJA-HEX-14-500"

    sku_40, _, _, _ = select_primary_screw_spec(Decimal("4.0"))
    assert sku_40 == "PIJA-HEX-14-650"
