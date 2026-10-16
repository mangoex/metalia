"""Pruebas unitarias para el Motor Geométrico de Naves y Cubiertas (RN-01, RN-02, RN-03, RN-04 y HU-01)."""

from decimal import Decimal


def test_rn01_slope_correction_factor_and_minimum_warning():
    """RN-01: Verifica el factor trigonométrico sqrt(1 + p^2) y la alerta cuando pendiente < 5%."""
    from app.services.geometry_engine import calculate_slope_factor

    # Pendiente 5% -> sqrt(1 + 0.05^2) = sqrt(1.0025) ≈ 1.001249
    res_5 = calculate_slope_factor(Decimal("5.0"), min_slope_pct=Decimal("5.0"))
    assert res_5.factor_pendiente == Decimal("1.001249")
    assert res_5.alerta_pendiente_minima is False

    # Pendiente 10% -> sqrt(1 + 0.10^2) = sqrt(1.01) ≈ 1.004988
    res_10 = calculate_slope_factor(Decimal("10.0"), min_slope_pct=Decimal("5.0"))
    assert res_10.factor_pendiente == Decimal("1.004988")
    assert res_10.alerta_pendiente_minima is False

    # Pendiente 15% -> sqrt(1 + 0.15^2) = sqrt(1.0225) ≈ 1.011187
    res_15 = calculate_slope_factor(Decimal("15.0"), min_slope_pct=Decimal("5.0"))
    assert res_15.factor_pendiente == Decimal("1.011187")

    # Pendiente 3% (< 5% mínimo recomendado) -> dispara advertencia técnica
    res_low = calculate_slope_factor(Decimal("3.0"), min_slope_pct=Decimal("5.0"))
    assert res_low.alerta_pendiente_minima is True
    assert "menor al 5% mínimo recomendado" in res_low.mensaje_alerta


def test_hu01_canonical_nave_40x25_two_waters_galvatecho_1_5_in(store):
    """
    HU-01 (Criterio Gherkin Exacto):
    Dado que el usuario ingresa L = 40 m, W = 25 m, techo a 2 aguas con pendiente del 5%
    y elige Galvatecho de 1.5'' (W_ef = 1.00 m, T_min = 0.1524 m),
    Cuando presiona 'Calcular Proyecto',
    Entonces:
    - Vertiente inclinada L_v = 12.5 * 1.001249 = 12.52 m (> 12.0 m de plataforma)
    - Divide cada faldón en k = 2 tramos de 6.33 m (incluyendo traslape de 0.1524 m)
    - Hileras por agua = 40 (80 hileras sumando las 2 aguas, 160 piezas físicas de 6.33 m)
    - Añade 6% de desperdicio informativo
    - Muestra Valor R (10.00) y peso total (~11.2 t de cubierta)
    """
    from app.models.domain import NaveGeometryInput
    from app.services.geometry_engine import calculate_nave_geometry

    inp = NaveGeometryInput(
        largo_nave_m=Decimal("40.0"),
        ancho_nave_m=Decimal("25.0"),
        altura_muro_m=Decimal("0.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("5.0"),
        area_huecos_m2=Decimal("0.0"),
        alcance_obra="SOLO_TECHO",
        sku_cubierta="GALVATECHO-15-2626-ARENA",
        sku_muro=None,
        desperdicio_cubierta_pct=Decimal("6.0"),
    )

    result = calculate_nave_geometry(inp, store)

    assert result.largo_vertiente_m == Decimal("12.52")
    assert result.supera_limite_plataforma is True
    assert result.tramos_por_vertiente == 2
    assert result.largo_tramo_cortado_m == Decimal("6.33")
    assert result.traslape_transversal_m == Decimal("0.1524")
    assert result.hileras_por_agua == 40
    assert result.hileras_totales_cubierta == 80
    assert result.piezas_totales_cubierta == 160
    assert result.valor_r_cubierta == Decimal("10.00")
    assert Decimal("10.0") <= result.peso_cubierta_ton <= Decimal("11.5")


def test_rn02_multytecho_transverse_overlap_200mm(store):
    """RN-02: Verifica que Multytecho aplique traslape transversal de 0.200 m (200 mm) cuando L_v > 12.00 m."""
    from app.models.domain import NaveGeometryInput
    from app.services.geometry_engine import calculate_nave_geometry

    inp = NaveGeometryInput(
        largo_nave_m=Decimal("30.0"),
        ancho_nave_m=Decimal("26.0"),
        altura_muro_m=Decimal("0.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("10.0"),
        area_huecos_m2=Decimal("0.0"),
        alcance_obra="SOLO_TECHO",
        sku_cubierta="MULTYTECHO-15-2626-BLANCO",
    )
    result = calculate_nave_geometry(inp, store)
    assert result.supera_limite_plataforma is True
    assert result.tramos_por_vertiente == 2
    assert result.traslape_transversal_m == Decimal("0.200")


def test_rn04_wall_effective_width_1067m_prevents_overestimation(store):
    """
    RN-04: Multymuro / Superwall DEBE usar ancho efectivo 1.067 m (no 1.000 m),
    evitando sobreestimar en 6.7% las piezas de fachada, y descontando área de vanos/huecos.
    """
    from app.models.domain import NaveGeometryInput
    from app.services.geometry_engine import calculate_nave_geometry

    # Nave de 20x12 m -> Perímetro = 64 m, Altura = 6 m -> Área bruta = 384 m2
    # Huecos = 24 m2 -> Área neta = 360 m2
    # Si usara 1.00 m daría 60 piezas; con 1.067 m (360 / (6 * 1.067) = 56.23) -> 57 piezas
    inp = NaveGeometryInput(
        largo_nave_m=Decimal("20.0"),
        ancho_nave_m=Decimal("12.0"),
        altura_muro_m=Decimal("6.0"),
        aguas_techo=2,
        pendiente_pct=Decimal("10.0"),
        area_huecos_m2=Decimal("24.0"),
        alcance_obra="NAVE_COMPLETA",
        sku_cubierta="GALVATECHO-15-2626-ARENA",
        sku_muro="MULTYMURO-15-2626-ARENA",
        desperdicio_muro_pct=Decimal("6.0"),
    )
    result = calculate_nave_geometry(inp, store)
    assert result.perimetro_m == Decimal("64.00")
    assert result.area_muro_neta_m2 == Decimal("360.00")
    assert result.area_muro_con_desperdicio_m2 == Decimal("381.60")
    assert result.ancho_efectivo_muro_m == Decimal("1.067")
    assert result.piezas_totales_muro == 57
