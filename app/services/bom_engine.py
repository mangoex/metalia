"""
Motor de Explosión de Materiales (BOM) para Pijas, Clips, Tapajuntas, Selladores y Remates (RN-06, RN-07, RN-08).
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.models.domain import (
    BOMExplosionResult,
    BOMItemResult,
    MetaliaInMemoryStore,
    NaveGeometryInput,
    NaveGeometryResult,
)

RENDIMIENTO_MOLDURA_305_M = Decimal("2.90")  # 3.05 m menos 0.15 m de traslape


def _ceil_int(val: Decimal) -> int:
    if val <= Decimal(0):
        return 0
    return int(val.to_integral_value(rounding=ROUND_CEILING))


def select_primary_screw_spec(espesor_pulg: Decimal | None) -> tuple[str, str, Decimal, Decimal]:
    """
    RN-06: Longitud de Pija Principal (pulgadas) = Espesor del Panel (pulgadas) + 2.5'' (o 2.75'' según cresta).
    Retorna (sku, descripcion, peso_unitario_kg, precio_unitario_mxn).
    """
    if espesor_pulg is None or espesor_pulg <= Decimal(0):
        return (
            "PIJA-HEX-14-100",
            "Pija Autotaladrante Galv. 1/4'' x 1'' con Arandela EPDM (Lámina Simple)",
            Decimal("0.012"),
            Decimal("2.10"),
        )
    if espesor_pulg <= Decimal("1.0"):
        return (
            "PIJA-HEX-14-350",
            "Pija Autotaladrante Galv. 1/4'' x 3 1/2'' con Arandela EPDM (Panel 1.0'')",
            Decimal("0.024"),
            Decimal("4.20"),
        )
    if espesor_pulg <= Decimal("1.5"):
        return (
            "PIJA-HEX-14-400",
            "Pija Autotaladrante Galv. 1/4'' x 4'' con Arandela EPDM (Panel 1.5'')",
            Decimal("0.028"),
            Decimal("4.85"),
        )
    if espesor_pulg <= Decimal("2.0"):
        return (
            "PIJA-HEX-14-475",
            "Pija Autotaladrante Galv. 1/4'' x 4 3/4'' con Arandela EPDM (Panel 2.0'', regla espesor + 2.5'')",
            Decimal("0.032"),
            Decimal("5.60"),
        )
    if espesor_pulg <= Decimal("2.5"):
        return (
            "PIJA-HEX-14-500",
            "Pija Autotaladrante Galv. 1/4'' x 5'' con Arandela EPDM (Panel 2.5'')",
            Decimal("0.035"),
            Decimal("6.10"),
        )
    largo_pulg = espesor_pulg + Decimal("2.5")
    return (
        f"PIJA-HEX-14-{int(largo_pulg * 100)}",
        f"Pija Autotaladrante Galv. 1/4'' x {largo_pulg}'' con Arandela EPDM (Panel {espesor_pulg}'')",
        Decimal("0.042"),
        Decimal("7.50"),
    )


def _make_item(
    tipo_regla: str,
    sku: str,
    descripcion: str,
    unidad: str,
    cantidad: int,
    largo_pieza_m: Decimal | None,
    peso_unitario_kg: Decimal,
    precio_unitario_mxn: Decimal,
    es_obligatorio: bool = True,
    clave_prod_serv_sat: str = "31161500",
    clave_unidad_sat: str = "H87",
) -> BOMItemResult:
    peso_total = (Decimal(cantidad) * peso_unitario_kg).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    importe = (Decimal(cantidad) * precio_unitario_mxn).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return BOMItemResult(
        tipo_regla=tipo_regla,
        sku=sku,
        descripcion=descripcion,
        unidad=unidad,
        cantidad=cantidad,
        largo_pieza_m=largo_pieza_m,
        peso_unitario_kg=peso_unitario_kg,
        peso_total_kg=peso_total,
        precio_unitario_mxn=precio_unitario_mxn,
        importe_mxn=importe,
        es_obligatorio=es_obligatorio,
        clave_prod_serv_sat=clave_prod_serv_sat,
        clave_unidad_sat=clave_unidad_sat,
    )


def generate_bom_for_nave(
    inp: NaveGeometryInput,
    geo: NaveGeometryResult,
    store: MetaliaInMemoryStore,
) -> BOMExplosionResult:
    """
    Genera la Lista de Materiales (BOM) completa aplicando RN-06, RN-07 y RN-08.
    """
    items: list[BOMItemResult] = []
    incluye_techo = inp.alcance_obra in ("SOLO_TECHO", "NAVE_COMPLETA")
    incluye_muros = inp.alcance_obra in ("SOLO_MUROS", "NAVE_COMPLETA")

    if incluye_techo and inp.sku_cubierta and geo.area_cubierta_real_m2 > Decimal(0):
        var_cub = store.get_variante(inp.sku_cubierta)
        fam_cub = store.familias[var_cub.familia_id]
        # Partida de panel de cubierta opaco
        hileras_opacas = geo.hileras_opacas if geo.hileras_opacas > 0 else geo.hileras_por_agua
        cant_cub_opaca = inp.aguas_techo * geo.tramos_por_vertiente * hileras_opacas
        peso_pza_cub = (geo.largo_tramo_cortado_m * fam_cub.ancho_efectivo_m * var_cub.peso_kg_m2).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        precio_pza_cub = (geo.largo_tramo_cortado_m * fam_cub.ancho_efectivo_m * var_cub.precio_base_m2_mxn).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        items.append(
            _make_item(
                tipo_regla="CUBIERTA_OPACA",
                sku=var_cub.sku,
                descripcion=f"{var_cub.nombre_comercial} (Tramo {geo.largo_tramo_cortado_m} m)",
                unidad="PZA",
                cantidad=cant_cub_opaca,
                largo_pieza_m=geo.largo_tramo_cortado_m,
                peso_unitario_kg=peso_pza_cub,
                precio_unitario_mxn=precio_pza_cub,
                clave_prod_serv_sat=var_cub.clave_prod_serv_sat,
            )
        )

        # Franjas de iluminación translúcida (RN-14: Acrylit G10)
        if geo.hileras_luz_natural > 0:
            cant_trans = inp.aguas_techo * geo.tramos_por_vertiente * geo.hileras_luz_natural
            peso_pza_trans = (geo.largo_tramo_cortado_m * Decimal("2.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            precio_pza_trans = (geo.largo_tramo_cortado_m * Decimal("391.11")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            items.append(
                _make_item(
                    tipo_regla="TRANSLUCIDO",
                    sku="ACRYLIT-G10-BLANCO",
                    descripcion=f"Lámina Translúcida Acrylit G10 T-81 Blanco Lechoso (Tramo {geo.largo_tramo_cortado_m} m)",
                    unidad="PZA",
                    cantidad=cant_trans,
                    largo_pieza_m=geo.largo_tramo_cortado_m,
                    peso_unitario_kg=peso_pza_trans,
                    precio_unitario_mxn=precio_pza_trans,
                    clave_prod_serv_sat="30151500",
                )
            )
            items.append(
                _make_item(
                    tipo_regla="SELLADOR",
                    sku="SELLADOR-POLIURETANO-600ML",
                    descripcion="Sellador de Poliuretano Dymonic / Sikaflex Salchicha 600 ml (Empalmes Translúcidos)",
                    unidad="PZA",
                    cantidad=_ceil_int(Decimal(cant_trans) / Decimal(2)),
                    largo_pieza_m=None,
                    peso_unitario_kg=Decimal("0.75"),
                    precio_unitario_mxn=Decimal("260.00"),
                    clave_prod_serv_sat="31201600",
                )
            )

        # 1. RN-06: Pijas principales (8 pijas por m2)
        sku_pija, desc_pija, peso_pija, precio_pija = select_primary_screw_spec(
            var_cub.espesor_pulg
        )
        cant_pijas_princ = _ceil_int(geo.area_cubierta_real_m2 * Decimal(8))
        items.append(
            _make_item(
                tipo_regla="PIJA_PRINCIPAL",
                sku=sku_pija,
                descripcion=desc_pija,
                unidad="PZA",
                cantidad=cant_pijas_princ,
                largo_pieza_m=None,
                peso_unitario_kg=peso_pija,
                precio_unitario_mxn=precio_pija,
            )
        )

        # 2. RN-06: Pijas de costura / cosido de traslapes y remates (1/4'' x 1/2'' o 7/8'')
        cant_pijas_costura = _ceil_int(geo.area_cubierta_real_m2 * Decimal(4))
        items.append(
            _make_item(
                tipo_regla="PIJA_COSTURA",
                sku="PIJA-COSTURA-14-050",
                descripcion="Pija de Costura Autotaladrante 1/4'' x 1/2'' con Arandela EPDM (Traslapes y Molduras)",
                unidad="PZA",
                cantidad=cant_pijas_costura,
                largo_pieza_m=None,
                peso_unitario_kg=Decimal("0.008"),
                precio_unitario_mxn=Decimal("1.65"),
            )
        )

        # 3. RN-06: Clips de fijación según mecanismo
        if fam_cub.mecanismo_fijacion == "EXPUESTA_TRASLAPE" and var_cub.espesor_pulg is not None:
            cant_clips = _ceil_int(geo.area_cubierta_real_m2 * Decimal("2.5"))
            items.append(
                _make_item(
                    tipo_regla="CLIP_FIJACION",
                    sku="CLIP-GALVATECHO-CAL18",
                    descripcion="Clip / Arandela Especial Galvatecho/Glamet Cal. 18 (47x38 mm) con Sello EPDM",
                    unidad="PZA",
                    cantidad=cant_clips,
                    largo_pieza_m=None,
                    peso_unitario_kg=Decimal("0.035"),
                    precio_unitario_mxn=Decimal("6.80"),
                )
            )
        elif fam_cub.mecanismo_fijacion == "OCULTA_TAPAJUNTA":
            cant_clips_ocultos = _ceil_int(geo.area_cubierta_real_m2 * Decimal("2.5"))
            items.append(
                _make_item(
                    tipo_regla="CLIP_FIJACION",
                    sku="CLIP-MULTYTECHO-CAL16",
                    descripcion="Clip Oculto de Fijación Multytecho Cal. 16 Galvanizado",
                    unidad="PZA",
                    cantidad=cant_clips_ocultos,
                    largo_pieza_m=None,
                    peso_unitario_kg=Decimal("0.055"),
                    precio_unitario_mxn=Decimal("9.50"),
                )
            )
        elif fam_cub.mecanismo_fijacion == "ENGARGOLADA":
            cant_clips_kr = _ceil_int(geo.area_cubierta_real_m2 * Decimal("2.2"))
            items.append(
                _make_item(
                    tipo_regla="CLIP_FIJACION",
                    sku="CLIP-KR18-FIJO",
                    descripcion="Clip Engargolable Oculto para Sistema KR-18 Cal. 18",
                    unidad="PZA",
                    cantidad=cant_clips_kr,
                    largo_pieza_m=None,
                    peso_unitario_kg=Decimal("0.060"),
                    precio_unitario_mxn=Decimal("11.20"),
                )
            )

        # 4. RN-07: Tapajuntas exclusivos para Multytecho (OCULTA_TAPAJUNTA)
        if fam_cub.mecanismo_fijacion == "OCULTA_TAPAJUNTA":
            cant_tapajuntas = (
                inp.aguas_techo
                * geo.tramos_por_vertiente
                * max(0, geo.hileras_por_agua - 1)
            )
            peso_tapajunta_pieza = (geo.largo_tramo_cortado_m * Decimal("0.85")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            precio_tapajunta_pieza = (
                geo.largo_tramo_cortado_m * Decimal("95.00")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            items.append(
                _make_item(
                    tipo_regla="TAPAJUNTA",
                    sku="TAPAJUNTA-MULTYTECHO-26",
                    descripcion=f"Tapajunta Longitudinal Multytecho Cal. 26 Pintro (Tramo {geo.largo_tramo_cortado_m} m)",
                    unidad="PZA",
                    cantidad=cant_tapajuntas,
                    largo_pieza_m=geo.largo_tramo_cortado_m,
                    peso_unitario_kg=peso_tapajunta_pieza,
                    precio_unitario_mxn=precio_tapajunta_pieza,
                    clave_prod_serv_sat="30151500",
                )
            )

        # 5. RN-08: Caballete central (3.05 m con rendimiento 2.90 m) y tapas
        if inp.aguas_techo == 2:
            cant_caballetes = _ceil_int(inp.largo_nave_m / RENDIMIENTO_MOLDURA_305_M)
            items.append(
                _make_item(
                    tipo_regla="CABALLETE",
                    sku="MOLD-CABALLETE-305-26",
                    descripcion="Caballete Central Dentado / Liso Cal. 26 Pintro (Tramo 3.05 m, útil 2.90 m)",
                    unidad="PZA",
                    cantidad=cant_caballetes,
                    largo_pieza_m=Decimal("3.05"),
                    peso_unitario_kg=Decimal("6.80"),
                    precio_unitario_mxn=Decimal("485.00"),
                    clave_prod_serv_sat="30151500",
                )
            )
            items.append(
                _make_item(
                    tipo_regla="TAPA_CABALLETE",
                    sku="MOLD-TAPA-CAB-26",
                    descripcion="Tapa / Cierre Troquelado de Caballete Cal. 26 Pintro",
                    unidad="PZA",
                    cantidad=geo.hileras_por_agua * 2,
                    largo_pieza_m=Decimal("1.00"),
                    peso_unitario_kg=Decimal("0.45"),
                    precio_unitario_mxn=Decimal("68.00"),
                    clave_prod_serv_sat="30151500",
                )
            )

        # 6. RN-08: Canalones pluviales (3.05 m, rendimiento 2.90 m) y Bajadas (1 cada 12.00 m)
        metros_alero = Decimal(inp.aguas_techo) * inp.largo_nave_m
        cant_canalones = _ceil_int(metros_alero / RENDIMIENTO_MOLDURA_305_M)
        cant_bajadas = _ceil_int(metros_alero / Decimal("12.00"))
        items.append(
            _make_item(
                tipo_regla="CANALON",
                sku="MOLD-CANALON-305-24",
                descripcion="Canalón Pluvial Estándar Cal. 24 Pintro (Tramo 3.05 m, útil 2.90 m)",
                unidad="PZA",
                cantidad=cant_canalones,
                largo_pieza_m=Decimal("3.05"),
                peso_unitario_kg=Decimal("8.90"),
                precio_unitario_mxn=Decimal("620.00"),
                es_obligatorio=False,
                clave_prod_serv_sat="30151500",
            )
        )
        items.append(
            _make_item(
                tipo_regla="BAJADA_PLUVIAL",
                sku="ACC-BAJADA-PLUVIAL-4",
                descripcion="Kit de Bajada Pluvial 4'' con Boquilla y Abrazaderas (1 cada 12 m de alero)",
                unidad="KIT",
                cantidad=cant_bajadas,
                largo_pieza_m=Decimal("3.05"),
                peso_unitario_kg=Decimal("5.20"),
                precio_unitario_mxn=Decimal("540.00"),
                es_obligatorio=False,
                clave_prod_serv_sat="30151500",
            )
        )

        # 7. RN-08: Remates laterales / Botaguas (2 por agua * L_vertiente / 2.90 m)
        metros_botaguas = Decimal(2 * inp.aguas_techo) * geo.largo_vertiente_m
        cant_botaguas = _ceil_int(metros_botaguas / RENDIMIENTO_MOLDURA_305_M)
        items.append(
            _make_item(
                tipo_regla="BOTAGUAS_LATERAL",
                sku="MOLD-BOTAGUAS-305-26",
                descripcion="Remate Lateral / Botaguas Cal. 26 Pintro (Tramo 3.05 m, útil 2.90 m)",
                unidad="PZA",
                cantidad=cant_botaguas,
                largo_pieza_m=Decimal("3.05"),
                peso_unitario_kg=Decimal("5.40"),
                precio_unitario_mxn=Decimal("395.00"),
                clave_prod_serv_sat="30151500",
            )
        )

        # 8. RN-08: Cinta de Butilo (rollos de 10 m) y Sellador de Poliuretano
        metros_sellado = (
            inp.largo_nave_m * Decimal(inp.aguas_techo)
            + Decimal(geo.hileras_totales_cubierta) * Decimal("1.0")
        )
        cant_butilo = max(1, _ceil_int(metros_sellado / Decimal("10.0")))
        cant_sellador = max(2, _ceil_int(metros_sellado / Decimal("15.0")))
        items.append(
            _make_item(
                tipo_regla="CINTA_BUTILO",
                sku="SELL-CINTA-BUTILO-10M",
                descripcion="Rollo de Cinta de Butilo Impermeabilizante 10 m x 5 cm Adhesión Permanente",
                unidad="ROLLO",
                cantidad=cant_butilo,
                largo_pieza_m=Decimal("10.00"),
                peso_unitario_kg=Decimal("0.65"),
                precio_unitario_mxn=Decimal("155.00"),
            )
        )
        items.append(
            _make_item(
                tipo_regla="SELLADOR_PU",
                sku="SELL-CARTUCHO-PU-300",
                descripcion="Cartucho de Sellador Elastomérico de Poliuretano 300 ml Uso Industrial",
                unidad="PZA",
                cantidad=cant_sellador,
                largo_pieza_m=None,
                peso_unitario_kg=Decimal("0.42"),
                precio_unitario_mxn=Decimal("190.00"),
            )
        )

    # 9. RN-08: Subsistema de Muros (Canal U de desplante y Esquineros de 3.05 m)
    if incluye_muros and inp.altura_muro_m > Decimal(0) and geo.area_muro_neta_m2 > Decimal(0):
        cant_canal_u = _ceil_int(geo.perimetro_m / RENDIMIENTO_MOLDURA_305_M)
        cant_esquineros = 2 * _ceil_int(
            (Decimal(4) * inp.altura_muro_m) / RENDIMIENTO_MOLDURA_305_M
        )
        items.append(
            _make_item(
                tipo_regla="CANAL_U_BASE",
                sku="MOLD-CANAL-U-305-24",
                descripcion="Canal 'U' de Desplante para Muro Panel Cal. 24 Pintro (Tramo 3.05 m)",
                unidad="PZA",
                cantidad=cant_canal_u,
                largo_pieza_m=Decimal("3.05"),
                peso_unitario_kg=Decimal("5.10"),
                precio_unitario_mxn=Decimal("370.00"),
                clave_prod_serv_sat="30151500",
            )
        )
        items.append(
            _make_item(
                tipo_regla="ESQUINERO",
                sku="MOLD-ESQUINERO-305-26",
                descripcion="Esquinero Interior / Exterior para Fachada Panel Cal. 26 Pintro (Tramo 3.05 m)",
                unidad="PZA",
                cantidad=cant_esquineros,
                largo_pieza_m=Decimal("3.05"),
                peso_unitario_kg=Decimal("5.60"),
                precio_unitario_mxn=Decimal("410.00"),
                clave_prod_serv_sat="30151500",
            )
        )

    peso_total = sum((it.peso_total_kg for it in items), Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    importe_total = sum((it.importe_mxn for it in items), Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return BOMExplosionResult(
        items=items,
        peso_total_accesorios_kg=peso_total,
        importe_total_accesorios_mxn=importe_total,
    )
