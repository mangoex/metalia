"""
Motor Geométrico de Cuantificación de Naves Industriales y Cubiertas (RN-01, RN-02, RN-03, RN-04).
Implementa trigonometría exacta con Decimal para evitar errores de redondeo comercial.
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.models.domain import (
    MetaliaInMemoryStore,
    NaveGeometryInput,
    NaveGeometryResult,
    SlopeFactorResult,
)


def _ceil_int(val: Decimal) -> int:
    return int(val.to_integral_value(rounding=ROUND_CEILING))


def calculate_slope_factor(
    pendiente_pct: Decimal,
    min_slope_pct: Decimal = Decimal("5.0"),
) -> SlopeFactorResult:
    """
    RN-01: Factor de Corrección por Pendiente (f_p = sqrt(1 + (p/100)^2)).
    Dispara advertencia técnica si pendiente_pct < min_slope_pct (por defecto 5%).
    """
    p_ratio = pendiente_pct / Decimal(100)
    fp = (Decimal(1) + (p_ratio * p_ratio)).sqrt().quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )
    alerta = pendiente_pct < min_slope_pct
    if alerta:
        mensaje = (
            f"Advertencia técnica: Pendiente del {pendiente_pct}% es menor al "
            f"{min_slope_pct:.0f}% mínimo recomendado; sujeta a revisión técnica."
        )
    else:
        mensaje = f"Pendiente del {pendiente_pct}% cumple norma técnica (>= {min_slope_pct:.0f}%)."

    return SlopeFactorResult(
        pendiente_pct=pendiente_pct,
        factor_pendiente=fp,
        alerta_pendiente_minima=alerta,
        mensaje_alerta=mensaje,
    )


def calculate_nave_geometry(
    inp: NaveGeometryInput,
    store: MetaliaInMemoryStore,
) -> NaveGeometryResult:
    """
    Ejecuta las ecuaciones RN-01, RN-02, RN-03 y RN-04 para cuantificar cubierta y muros.
    """
    incluye_techo = inp.alcance_obra in ("SOLO_TECHO", "NAVE_COMPLETA")
    incluye_muros = inp.alcance_obra in ("SOLO_MUROS", "NAVE_COMPLETA")

    # Parámetros de familia de cubierta
    if incluye_techo and inp.sku_cubierta:
        var_cub = store.get_variante(inp.sku_cubierta)
        fam_cub = store.familias[var_cub.familia_id]
        min_slope = fam_cub.pendiente_minima_pct
        w_ef_cub = fam_cub.ancho_efectivo_m
        l_max_plat = fam_cub.largo_max_plataforma_m
        t_min = fam_cub.traslape_transversal_min_m
        valor_r_cub = var_cub.valor_r
        peso_kg_m2_cub = var_cub.peso_kg_m2
    else:
        min_slope = Decimal("5.0")
        w_ef_cub = Decimal("1.000")
        l_max_plat = Decimal("12.00")
        t_min = Decimal("0.1524")
        valor_r_cub = Decimal("0.00")
        peso_kg_m2_cub = Decimal("0.00")

    slope_res = calculate_slope_factor(inp.pendiente_pct, min_slope_pct=min_slope)
    fp = slope_res.factor_pendiente

    # RN-02: Vertiente y partición longitudinal (> 12.00 m)
    if incluye_techo:
        w_vertiente = (
            inp.ancho_nave_m
            if inp.aguas_techo == 1
            else (inp.ancho_nave_m / Decimal(2))
        )
        lv_exact = w_vertiente * fp
        lv_rounded = lv_exact.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if lv_exact > l_max_plat and not inp.rolado_en_sitio:
            supera_plat = True
            k = _ceil_int(lv_exact / l_max_plat)
            traslape_aplicado = t_min
            # En cálculos de ingeniería del sector (ver HU-01: 12.5 + 0.1524 / 2 = 6.3262 -> 6.33 m)
            l_tramo = (
                (lv_exact + Decimal(k - 1) * traslape_aplicado) / Decimal(k)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            supera_plat = False
            k = 1
            traslape_aplicado = Decimal("0.0000")
            l_tramo = lv_rounded

        # RN-03: Conteo de piezas de cubierta
        n_hileras_agua = _ceil_int(inp.largo_nave_m / w_ef_cub)
        n_hileras_totales = inp.aguas_techo * n_hileras_agua
        n_piezas_cub = inp.aguas_techo * k * n_hileras_agua

        area_planta = (inp.largo_nave_m * inp.ancho_nave_m).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_cub_real = (area_planta * fp).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        desp_cub_ratio = inp.desperdicio_cubierta_pct / Decimal(100)
        area_cub_desp = (area_cub_real * (Decimal(1) + desp_cub_ratio)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_cub_facturada = (
            Decimal(n_piezas_cub) * l_tramo * w_ef_cub
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # Peso de cubierta considerando el área con desperdicio/traslapes reales
        peso_cub_kg = (
            max(area_cub_desp, area_cub_facturada) * peso_kg_m2_cub
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        peso_cub_ton = (peso_cub_kg / Decimal(1000)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        w_vertiente = Decimal("0.00")
        lv_rounded = Decimal("0.00")
        supera_plat = False
        k = 0
        l_tramo = Decimal("0.00")
        traslape_aplicado = Decimal("0.0000")
        n_hileras_agua = 0
        n_hileras_totales = 0
        n_piezas_cub = 0
        area_planta = (inp.largo_nave_m * inp.ancho_nave_m).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_cub_real = Decimal("0.00")
        area_cub_desp = Decimal("0.00")
        area_cub_facturada = Decimal("0.00")
        peso_cub_kg = Decimal("0.00")
        peso_cub_ton = Decimal("0.00")

    # RN-04: Cálculo geométrico de muros y fachadas (ancho efectivo 1.067 m en Multymuro/Superwall)
    perimetro = (Decimal(2) * (inp.largo_nave_m + inp.ancho_nave_m)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if incluye_muros and inp.altura_muro_m > Decimal(0) and inp.sku_muro:
        var_muro = store.get_variante(inp.sku_muro)
        fam_muro = store.familias[var_muro.familia_id]
        w_ef_muro = fam_muro.ancho_efectivo_m
        area_muro_bruta = (perimetro * inp.altura_muro_m).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_muro_neta = max(Decimal("0.00"), area_muro_bruta - inp.area_huecos_m2).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        desp_muro_ratio = inp.desperdicio_muro_pct / Decimal(100)
        area_muro_desp = (area_muro_neta * (Decimal(1) + desp_muro_ratio)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_por_pieza_muro = inp.altura_muro_m * w_ef_muro
        n_piezas_muro = (
            _ceil_int(area_muro_neta / area_por_pieza_muro)
            if area_por_pieza_muro > Decimal(0)
            else 0
        )
        area_muro_facturada = (
            Decimal(n_piezas_muro) * inp.altura_muro_m * w_ef_muro
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        peso_muro_kg = (area_muro_facturada * var_muro.peso_kg_m2).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        peso_muro_ton = (peso_muro_kg / Decimal(1000)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        w_ef_muro = Decimal("1.067")
        area_muro_bruta = Decimal("0.00")
        area_muro_neta = Decimal("0.00")
        area_muro_desp = Decimal("0.00")
        n_piezas_muro = 0
        area_muro_facturada = Decimal("0.00")
        peso_muro_kg = Decimal("0.00")
        peso_muro_ton = Decimal("0.00")

    peso_total_kg = (peso_cub_kg + peso_muro_kg).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    peso_total_ton = (peso_total_kg / Decimal(1000)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return NaveGeometryResult(
        factor_pendiente=fp,
        alerta_pendiente_minima=slope_res.alerta_pendiente_minima,
        mensaje_alerta_pendiente=slope_res.mensaje_alerta,
        ancho_vertiente_m=w_vertiente.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        largo_vertiente_m=lv_rounded,
        supera_limite_plataforma=supera_plat,
        tramos_por_vertiente=k,
        largo_tramo_cortado_m=l_tramo,
        traslape_transversal_m=traslape_aplicado,
        ancho_efectivo_cubierta_m=w_ef_cub,
        hileras_por_agua=n_hileras_agua,
        hileras_totales_cubierta=n_hileras_totales,
        piezas_totales_cubierta=n_piezas_cub,
        area_planta_m2=area_planta,
        area_cubierta_real_m2=area_cub_real,
        area_cubierta_con_desperdicio_m2=area_cub_desp,
        area_cubierta_facturada_m2=area_cub_facturada,
        valor_r_cubierta=valor_r_cub,
        peso_cubierta_kg=peso_cub_kg,
        peso_cubierta_ton=peso_cub_ton,
        perimetro_m=perimetro,
        area_muro_bruta_m2=area_muro_bruta,
        area_muro_neta_m2=area_muro_neta,
        area_muro_con_desperdicio_m2=area_muro_desp,
        ancho_efectivo_muro_m=w_ef_muro,
        piezas_totales_muro=n_piezas_muro,
        area_muro_facturada_m2=area_muro_facturada,
        peso_muro_kg=peso_muro_kg,
        peso_muro_ton=peso_muro_ton,
        peso_total_paneles_kg=peso_total_kg,
        peso_total_paneles_ton=peso_total_ton,
    )
