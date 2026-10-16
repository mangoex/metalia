"""
Servicio de Tarificación, Vigencia de Cotizaciones (72 horas hábiles), Reserva de Stock por Anticipo 50%
y Cotización de Mano de Obra de Instalación y Estructura Secundaria (HU-01 a HU-06).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from urllib.parse import quote_plus

from app.models.domain import (
    CotizacionProyecto,
    CreateDirectQuoteRequest,
    CreateNaveQuoteRequest,
    MetaliaInMemoryStore,
    NaveGeometryInput,
    PartidaCotizacion,
)
from app.services.bom_engine import generate_bom_for_nave
from app.services.freight_service import calculate_destination_freight
from app.services.geometry_engine import calculate_nave_geometry
from app.services.inventory_service import evaluate_direct_line_stock
from app.services.logistics_carta_porte import determine_transport_unit_and_freight

TARIFA_INSTALACION_CUBIERTA_M2_MXN = Decimal("285.00")
TARIFA_INSTALACION_MURO_M2_MXN = Decimal("310.00")
VIGENCIA_HORAS_HABILES = 72


def calculate_commercial_cascade(
    precio_lista_base_m2: Decimal,
    descuento_planta_pct: Decimal = Decimal("0.34"),
    indirecto_pct: Decimal = Decimal("0.00"),
    margen_utilidad_pct: Decimal = Decimal("0.25"),
    es_espuma_fm: bool = False,
    flete_unitario_m2: Decimal = Decimal("0.00"),
) -> dict[str, Decimal | bool]:
    """
    RN-11: Estructura Comercial en Cascada con factor Espuma FM (+7%) y RN-12: Trazabilidad de Margen.
    """
    if es_espuma_fm:
        precio_lista_ajustado = (precio_lista_base_m2 * Decimal("1.07")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        precio_lista_ajustado = precio_lista_base_m2.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    costo_neto_compra = (precio_lista_ajustado * (Decimal("1.0") - descuento_planta_pct)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    costo_con_indirecto = (costo_neto_compra * (Decimal("1.0") + indirecto_pct)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    precio_venta_sin_flete = (costo_con_indirecto * (Decimal("1.0") + margen_utilidad_pct)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    utilidad_bruta = (precio_venta_sin_flete - costo_con_indirecto).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if precio_venta_sin_flete > Decimal(0):
        margen_bruto_pct = ((utilidad_bruta / precio_venta_sin_flete) * Decimal("100.0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        margen_bruto_pct = Decimal("0.00")

    pu_final = (precio_venta_sin_flete + flete_unitario_m2).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    alerta_margen = margen_bruto_pct < Decimal("15.00")

    return {
        "precio_lista_ajustado_m2": precio_lista_ajustado,
        "costo_neto_compra_m2": costo_neto_compra,
        "costo_con_indirecto_m2": costo_con_indirecto,
        "precio_venta_sin_flete_m2": precio_venta_sin_flete,
        "utilidad_bruta_m2": utilidad_bruta,
        "margen_bruto_pct": margen_bruto_pct,
        "pu_final_con_flete_m2": pu_final,
        "alerta_margen_bajo": alerta_margen,
    }


def _add_business_hours(start_dt: datetime, business_hours: int = 72) -> datetime:
    """Suma horas hábiles (lunes a viernes, 24h por día hábil equivale a 3 días hábiles)."""
    current = start_dt
    remaining_hours = business_hours
    while remaining_hours > 0:
        current += timedelta(hours=1)
        if current.weekday() < 5:  # 0=Lunes .. 4=Viernes
            remaining_hours -= 1
    return current


def _build_whatsapp_url(folio: str, cliente_nombre: str, total_mxn: Decimal, peso_ton: Decimal) -> str:
    msg = (
        f"Hola Metalia Querétaro, soy {cliente_nombre}. "
        f"Solicito seguimiento a mi cotización {folio} por ${total_mxn:,.2f} MXN "
        f"(Peso estimado: {peso_ton} Ton). Quedo atento para el pago del 50% de anticipo."
    )
    return f"https://wa.me/524421002000?text={quote_plus(msg)}"


def create_direct_quote(
    req: CreateDirectQuoteRequest,
    store: MetaliaInMemoryStore,
) -> CotizacionProyecto:
    """
    Modo A: Crea una cotización formal por despiece directo (HU-02), verificando inventario
    dimensional en piso en Querétaro, corte de hoja maestra o fabricación en planta.
    """
    emitted_at = req.fecha_emision_override or datetime.now(UTC)
    expires_at = _add_business_hours(emitted_at, VIGENCIA_HORAS_HABILES)
    partidas: list[PartidaCotizacion] = []
    largo_max = Decimal("0.00")

    for line in req.lineas:
        var = store.get_variante(line.sku)
        fam = store.familias[var.familia_id]
        alloc = evaluate_direct_line_stock(
            store=store,
            sku=line.sku,
            cantidad_piezas=line.cantidad_piezas,
            largo_requerido_m=line.largo_pieza_m,
        )
        largo_max = max(largo_max, line.largo_pieza_m)

        subsistema = "MURO" if fam.codigo_familia == "PANEL_MURO" else "CUBIERTA"
        precio_pieza = (alloc.importe_mxn / Decimal(line.cantidad_piezas)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        partidas.append(
            PartidaCotizacion(
                subsistema=subsistema,
                sku=line.sku,
                descripcion=(
                    f"{var.nombre_comercial} — {line.cantidad_piezas} pzas de "
                    f"{line.largo_pieza_m:.2f} m ({alloc.area_m2_facturada:.2f} m²)"
                ),
                cantidad_piezas=line.cantidad_piezas,
                unidad="PZA",
                largo_pieza_m=line.largo_pieza_m,
                largo_facturado_m=alloc.largo_facturado_m,
                area_m2_facturada=alloc.area_m2_facturada,
                peso_partida_kg=alloc.peso_total_kg,
                origen_suministro=alloc.origen_suministro,
                distintivo_disponibilidad=alloc.distintivo_disponibilidad,
                precio_unitario_mxn=precio_pieza,
                importe_mxn=alloc.importe_mxn,
                clave_prod_serv_sat=var.clave_prod_serv_sat,
                clave_unidad_sat=var.clave_unidad_sat,
                id_lote_reservable=alloc.id_lote_asignado,
                es_mercancia_fisica=True,
            )
        )

    if req.incluir_instalacion:
        area_total_m2 = sum((p.area_m2_facturada for p in partidas), Decimal("0.00"))
        imp_inst = (area_total_m2 * TARIFA_INSTALACION_CUBIERTA_M2_MXN).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        partidas.append(
            PartidaCotizacion(
                subsistema="INSTALACION",
                sku="SERV-INST-METALIA",
                descripcion=f"Servicio de Instalación y Montaje Certificado Metalia ({area_total_m2:.2f} m²)",
                cantidad_piezas=1,
                unidad="SERV",
                area_m2_facturada=area_total_m2,
                peso_partida_kg=Decimal("0.00"),
                origen_suministro="STOCK_EXACTO_PISO",
                distintivo_disponibilidad="Cuadrilla Certificada en Querétaro y Bajío",
                precio_unitario_mxn=imp_inst,
                importe_mxn=imp_inst,
                clave_prod_serv_sat="72151900",
                clave_unidad_sat="E48",
                es_mercancia_fisica=False,
            )
        )

    peso_bruto_kg = sum(
        (p.peso_partida_kg for p in partidas if p.es_mercancia_fisica), Decimal("0.00")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    unidad_transp, costo_flete = determine_transport_unit_and_freight(
        peso_total_kg=peso_bruto_kg,
        largo_max_pieza_m=largo_max,
        codigo_postal_destino=req.codigo_postal_obra,
        tipo_entrega=req.tipo_entrega,
    )
    if req.tipo_entrega == "FLETE_OBRA" and costo_flete > Decimal("0.00"):
        partidas.append(
            PartidaCotizacion(
                subsistema="FLETE",
                sku="SERV-FLETE-METALIA",
                descripcion=f"Flete Especializado a Obra (CP {req.codigo_postal_obra}) — {unidad_transp}",
                cantidad_piezas=1,
                unidad="SERV",
                peso_partida_kg=Decimal("0.00"),
                origen_suministro="STOCK_EXACTO_PISO",
                distintivo_disponibilidad="Incluye Pre-Validación Carta Porte 3.1 SAT",
                precio_unitario_mxn=costo_flete,
                importe_mxn=costo_flete,
                clave_prod_serv_sat="78101800",
                clave_unidad_sat="E48",
                es_mercancia_fisica=False,
            )
        )

    subtotal = sum((p.importe_mxn for p in partidas), Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    anticipo = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    liquidacion = (total - anticipo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    peso_ton = (peso_bruto_kg / Decimal(1000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    folio = store.next_folio()
    quote = CotizacionProyecto(
        folio=folio,
        modo_captura="DIRECTO_DESPIECE",
        cliente_nombre=req.cliente_nombre,
        cliente_empresa=req.cliente_empresa,
        cliente_whatsapp=req.cliente_whatsapp,
        cliente_email=req.cliente_email,
        cliente_rfc=req.cliente_rfc,
        codigo_postal_obra=req.codigo_postal_obra,
        tipo_entrega=req.tipo_entrega,
        estado="ENVIADA",
        fecha_emision=emitted_at,
        fecha_vigencia=expires_at,
        partidas=partidas,
        peso_bruto_total_kg=peso_bruto_kg,
        peso_bruto_total_ton=peso_ton,
        unidad_transporte_sugerida=unidad_transp,
        subtotal_mxn=subtotal,
        iva_mxn=iva,
        total_mxn=total,
        anticipo_50_mxn=anticipo,
        liquidacion_50_mxn=liquidacion,
        whatsapp_share_url=_build_whatsapp_url(folio, req.cliente_nombre, total, peso_ton),
    )
    store.cotizaciones[folio] = quote
    return quote


def create_nave_quote(
    req: CreateNaveQuoteRequest,
    store: MetaliaInMemoryStore,
) -> CotizacionProyecto:
    """
    Modo B: Crea una cotización integral de Nave Industrial (HU-01, HU-03, HU-04),
    combinando el cálculo geométrico de cubierta/muros, la explosión BOM de accesorios,
    estructura secundaria opcional de polín Monten, mano de obra de instalación y flete.
    """
    emitted_at = req.fecha_emision_override or datetime.now(UTC)
    expires_at = _add_business_hours(emitted_at, VIGENCIA_HORAS_HABILES)

    geo_inp = NaveGeometryInput(
        largo_nave_m=req.largo_nave_m,
        ancho_nave_m=req.ancho_nave_m,
        altura_muro_m=req.altura_muro_m,
        aguas_techo=req.aguas_techo,
        pendiente_pct=req.pendiente_pct,
        area_huecos_m2=req.area_huecos_m2,
        alcance_obra=req.alcance_obra,
        sku_cubierta=req.sku_cubierta,
        sku_muro=req.sku_muro,
        desperdicio_cubierta_pct=req.desperdicio_cubierta_pct,
        desperdicio_muro_pct=req.desperdicio_muro_pct,
        porcentaje_luz_natural_pct=req.porcentaje_luz_natural_pct,
    )
    geo = calculate_nave_geometry(geo_inp, store)
    partidas: list[PartidaCotizacion] = []
    largo_max = Decimal("0.00")

    # 1. Partida de Cubierta
    cant_piezas_cub = (
        req.aguas_techo * geo.tramos_por_vertiente * geo.hileras_opacas
        if geo.hileras_luz_natural > 0
        else geo.piezas_totales_cubierta
    )
    if req.alcance_obra in ("SOLO_TECHO", "NAVE_COMPLETA") and req.sku_cubierta and cant_piezas_cub > 0:
        var_cub = store.get_variante(req.sku_cubierta)
        alloc_cub = evaluate_direct_line_stock(
            store=store,
            sku=req.sku_cubierta,
            cantidad_piezas=cant_piezas_cub,
            largo_requerido_m=geo.largo_tramo_cortado_m,
        )
        largo_max = max(largo_max, geo.largo_tramo_cortado_m)
        precio_pza_cub = (
            alloc_cub.importe_mxn / Decimal(cant_piezas_cub)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        partidas.append(
            PartidaCotizacion(
                subsistema="CUBIERTA",
                sku=req.sku_cubierta,
                descripcion=(
                    f"{var_cub.nombre_comercial} — {cant_piezas_cub} tramos de "
                    f"{geo.largo_tramo_cortado_m:.2f} m ({geo.tramos_por_vertiente} tramo(s)/agua)"
                ),
                cantidad_piezas=cant_piezas_cub,
                unidad="PZA",
                largo_pieza_m=geo.largo_tramo_cortado_m,
                largo_facturado_m=alloc_cub.largo_facturado_m,
                area_m2_facturada=alloc_cub.area_m2_facturada,
                peso_partida_kg=geo.peso_cubierta_kg,
                origen_suministro=alloc_cub.origen_suministro,
                distintivo_disponibilidad=alloc_cub.distintivo_disponibilidad,
                precio_unitario_mxn=precio_pza_cub,
                importe_mxn=alloc_cub.importe_mxn,
                clave_prod_serv_sat=var_cub.clave_prod_serv_sat,
                clave_unidad_sat=var_cub.clave_unidad_sat,
                id_lote_reservable=alloc_cub.id_lote_asignado,
                es_mercancia_fisica=True,
            )
        )

    # 2. Partida de Muros Perimetrales
    if req.alcance_obra in ("SOLO_MUROS", "NAVE_COMPLETA") and req.sku_muro and geo.piezas_totales_muro > 0:
        var_muro = store.get_variante(req.sku_muro)
        alloc_muro = evaluate_direct_line_stock(
            store=store,
            sku=req.sku_muro,
            cantidad_piezas=geo.piezas_totales_muro,
            largo_requerido_m=req.altura_muro_m,
        )
        largo_max = max(largo_max, req.altura_muro_m)
        precio_pza_muro = (
            alloc_muro.importe_mxn / Decimal(geo.piezas_totales_muro)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        partidas.append(
            PartidaCotizacion(
                subsistema="MURO",
                sku=req.sku_muro,
                descripcion=(
                    f"{var_muro.nombre_comercial} — {geo.piezas_totales_muro} piezas de "
                    f"{req.altura_muro_m:.2f} m (Ancho ef. {geo.ancho_efectivo_muro_m} m)"
                ),
                cantidad_piezas=geo.piezas_totales_muro,
                unidad="PZA",
                largo_pieza_m=req.altura_muro_m,
                largo_facturado_m=alloc_muro.largo_facturado_m,
                area_m2_facturada=alloc_muro.area_m2_facturada,
                peso_partida_kg=geo.peso_muro_kg,
                origen_suministro=alloc_muro.origen_suministro,
                distintivo_disponibilidad=alloc_muro.distintivo_disponibilidad,
                precio_unitario_mxn=precio_pza_muro,
                importe_mxn=alloc_muro.importe_mxn,
                clave_prod_serv_sat=var_muro.clave_prod_serv_sat,
                clave_unidad_sat=var_muro.clave_unidad_sat,
                id_lote_reservable=alloc_muro.id_lote_asignado,
                es_mercancia_fisica=True,
            )
        )

    # 3. Explosión BOM de Accesorios, Pijas, Clips, Selladores y Remates (HU-03, RN-14)
    if req.incluir_bom_accesorios:
        bom = generate_bom_for_nave(geo_inp, geo, store)
        for item in bom.items:
            if item.tipo_regla == "CUBIERTA_OPACA":
                continue  # Ya cuantificada y evaluada en piso en la Partida 1
            partidas.append(
                PartidaCotizacion(
                    subsistema="ACCESORIO_BOM",
                    sku=item.sku,
                    descripcion=item.descripcion,
                    cantidad_piezas=item.cantidad,
                    unidad=item.unidad,
                    largo_pieza_m=item.largo_pieza_m,
                    largo_facturado_m=item.largo_pieza_m,
                    area_m2_facturada=Decimal("0.00"),
                    peso_partida_kg=item.peso_total_kg,
                    origen_suministro="STOCK_EXACTO_PISO",
                    distintivo_disponibilidad="Disponible en Almacén de Accesorios Querétaro",
                    precio_unitario_mxn=item.precio_unitario_mxn,
                    importe_mxn=item.importe_mxn,
                    clave_prod_serv_sat=item.clave_prod_serv_sat,
                    clave_unidad_sat=item.clave_unidad_sat,
                    es_mercancia_fisica=True,
                )
            )

    # 4. Estructura Secundaria de Polín Monten C-200 Cal. 14 en tramos de 6.00 m (Opcional)
    if req.incluir_estructura_polin and geo.largo_vertiente_m > Decimal(0):
        lineas_polin_por_agua = int(
            (geo.largo_vertiente_m / Decimal("2.20")).to_integral_value(rounding=ROUND_CEILING)
        ) + 1
        metros_totales_polin = (
            Decimal(req.aguas_techo * lineas_polin_por_agua) * req.largo_nave_m
        )
        tramos_polin_6m = int(
            (metros_totales_polin / Decimal("6.00")).to_integral_value(rounding=ROUND_CEILING)
        )
        peso_polin_kg = (Decimal(tramos_polin_6m) * Decimal("28.50")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        precio_polin_unit = Decimal("980.00")
        importe_polin = (Decimal(tramos_polin_6m) * precio_polin_unit).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        largo_max = max(largo_max, Decimal("6.00"))
        partidas.append(
            PartidaCotizacion(
                subsistema="ESTRUCTURA_SECUNDARIA",
                sku="POLIN-MONTEN-C200-14-6M",
                descripcion="Polín Estructural Monten C-200 Cal. 14 Galvanizado/Pintado (Tramo 6.00 m)",
                cantidad_piezas=tramos_polin_6m,
                unidad="PZA",
                largo_pieza_m=Decimal("6.00"),
                largo_facturado_m=Decimal("6.00"),
                peso_partida_kg=peso_polin_kg,
                origen_suministro="STOCK_EXACTO_PISO",
                distintivo_disponibilidad="Disponible en Patio Estructural Querétaro",
                precio_unitario_mxn=precio_polin_unit,
                importe_mxn=importe_polin,
                clave_prod_serv_sat="30101700",
                clave_unidad_sat="H87",
                es_mercancia_fisica=True,
            )
        )

    # 5. Servicio de Instalación y Montaje Metalia por m² (HU-04)
    if req.incluir_instalacion:
        imp_inst_cub = (
            geo.area_cubierta_real_m2 * TARIFA_INSTALACION_CUBIERTA_M2_MXN
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        imp_inst_muro = (
            geo.area_muro_neta_m2 * TARIFA_INSTALACION_MURO_M2_MXN
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        imp_inst_total = (imp_inst_cub + imp_inst_muro).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        area_inst_total = (geo.area_cubierta_real_m2 + geo.area_muro_neta_m2).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        partidas.append(
            PartidaCotizacion(
                subsistema="INSTALACION",
                sku="SERV-INST-LLAVE-MANO",
                descripcion=(
                    f"Mano de Obra de Instalación y Montaje Certificado Metalia "
                    f"(Cubierta: {geo.area_cubierta_real_m2:.2f} m² + Muro: {geo.area_muro_neta_m2:.2f} m²)"
                ),
                cantidad_piezas=1,
                unidad="SERV",
                area_m2_facturada=area_inst_total,
                peso_partida_kg=Decimal("0.00"),
                origen_suministro="STOCK_EXACTO_PISO",
                distintivo_disponibilidad="Ingeniería y Cuadrilla Certificada DC-3 (Alturas)",
                precio_unitario_mxn=imp_inst_total,
                importe_mxn=imp_inst_total,
                clave_prod_serv_sat="72151900",
                clave_unidad_sat="E48",
                es_mercancia_fisica=False,
            )
        )

    peso_bruto_kg = sum(
        (p.peso_partida_kg for p in partidas if p.es_mercancia_fisica), Decimal("0.00")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    unidad_transp, costo_flete_fallback = determine_transport_unit_and_freight(
        peso_total_kg=peso_bruto_kg,
        largo_max_pieza_m=largo_max,
        codigo_postal_destino=req.codigo_postal_obra,
        tipo_entrega=req.tipo_entrega,
    )

    if req.estado_destino and req.municipio_destino:
        espesor_str = None
        if req.sku_cubierta and req.sku_cubierta in store.variantes:
            esp = store.variantes[req.sku_cubierta].espesor_pulg
            if esp is not None:
                espesor_str = f"{esp}\""
        ml_cub = Decimal(geo.piezas_totales_cubierta) * geo.largo_tramo_cortado_m
        flete_res = calculate_destination_freight(
            estado=req.estado_destino,
            municipio=req.municipio_destino,
            tipo_aplicacion="TECHO",
            espesor_pulg=espesor_str,
            longitud_total_ml=ml_cub,
            peso_total_kg=peso_bruto_kg,
        )
        costo_flete = flete_res["costo_flete_mxn"]
        descripcion_flete = (
            f"Flete Nacional Especializado a {req.estado_destino} — {flete_res['destino']} "
            f"({flete_res['metodo_calculo']}) — {unidad_transp}"
        )
    else:
        costo_flete = costo_flete_fallback
        descripcion_flete = f"Flete Especializado a Obra (CP {req.codigo_postal_obra}) — {unidad_transp}"

    if req.tipo_entrega == "FLETE_OBRA" and costo_flete > Decimal("0.00"):
        partidas.append(
            PartidaCotizacion(
                subsistema="FLETE",
                sku="SERV-FLETE-METALIA",
                descripcion=descripcion_flete,
                cantidad_piezas=1,
                unidad="SERV",
                peso_partida_kg=Decimal("0.00"),
                origen_suministro="STOCK_EXACTO_PISO",
                distintivo_disponibilidad="Incluye Pre-Validación Carta Porte 3.1 SAT",
                precio_unitario_mxn=costo_flete,
                importe_mxn=costo_flete,
                clave_prod_serv_sat="78101800",
                clave_unidad_sat="E48",
                es_mercancia_fisica=False,
            )
        )

    importe_venta_sin_flete = sum(
        (p.importe_mxn for p in partidas if p.subsistema != "FLETE"), Decimal("0.00")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    costo_material = (
        importe_venta_sin_flete / (Decimal("1.0") + req.margen_utilidad_pct)
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    utilidad_bruta = (importe_venta_sin_flete - costo_material).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    margen_pct = (
        ((utilidad_bruta / importe_venta_sin_flete) * Decimal("100.0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if importe_venta_sin_flete > Decimal(0)
        else Decimal("0.00")
    )

    subtotal = sum((p.importe_mxn for p in partidas), Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    anticipo = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    liquidacion = (total - anticipo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    peso_ton = (peso_bruto_kg / Decimal(1000)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    folio = store.next_folio()
    quote = CotizacionProyecto(
        folio=folio,
        modo_captura="GEOMETRICO_NAVE",
        cliente_nombre=req.cliente_nombre,
        cliente_empresa=req.cliente_empresa,
        cliente_whatsapp=req.cliente_whatsapp,
        cliente_email=req.cliente_email,
        cliente_rfc=req.cliente_rfc,
        codigo_postal_obra=req.codigo_postal_obra,
        tipo_entrega=req.tipo_entrega,
        estado="ENVIADA",
        fecha_emision=emitted_at,
        fecha_vigencia=expires_at,
        resumen_geometrico=geo,
        partidas=partidas,
        peso_bruto_total_kg=peso_bruto_kg,
        peso_bruto_total_ton=peso_ton,
        unidad_transporte_sugerida=unidad_transp,
        costo_total_material_mxn=costo_material,
        importe_venta_sin_flete_mxn=importe_venta_sin_flete,
        utilidad_bruta_mxn=utilidad_bruta,
        margen_bruto_pct=margen_pct,
        alerta_margen_bajo=margen_pct < Decimal("15.00"),
        estado_destino=req.estado_destino,
        municipio_destino=req.municipio_destino,
        es_espuma_fm=req.es_espuma_fm,
        subtotal_mxn=subtotal,
        iva_mxn=iva,
        total_mxn=total,
        anticipo_50_mxn=anticipo,
        liquidacion_50_mxn=liquidacion,
        whatsapp_share_url=_build_whatsapp_url(folio, req.cliente_nombre, total, peso_ton),
    )
    store.cotizaciones[folio] = quote
    return quote


def check_and_update_quote_validity(
    quote: CotizacionProyecto,
    current_time: datetime | None = None,
) -> CotizacionProyecto:
    """
    HU-06: Verifica si la cotización ha superado las 72 horas hábiles de vigencia
    sin que se haya pagado el anticipo del 50%.
    """
    now = current_time or datetime.now(UTC)
    if quote.estado in ("BORRADOR", "ENVIADA") and now > quote.fecha_vigencia:
        quote.estado = "EXPIRADA"
        quote.mensaje_vigencia = (
            "Cotización Expirada por Vigencia de Precios del Acero (72 horas hábiles vencidas). "
            "Ejecute recálculo al precio y stock del día."
        )
    return quote


def register_advance_payment(
    folio: str,
    store: MetaliaInMemoryStore,
    current_time: datetime | None = None,
) -> CotizacionProyecto:
    """
    Registra el pago del 50% de anticipo y coloca en estado RESERVADO las piezas
    de Inventario_Dimensional_Piso correspondientes.
    """
    if folio not in store.cotizaciones:
        raise KeyError(f"Folio de cotización no encontrado: {folio}")
    quote = store.cotizaciones[folio]
    check_and_update_quote_validity(quote, current_time=current_time)

    if quote.estado == "EXPIRADA":
        raise ValueError(
            "Cotización Expirada por Vigencia de Precios del Acero. "
            "No es posible procesar el anticipo sin recalcular al precio vigente."
        )

    for p in quote.partidas:
        if p.id_lote_reservable:
            lot = next(
                (l for l in store.inventario_piso if l.id_lote == p.id_lote_reservable),
                None,
            )
            if lot and lot.cantidad_piezas_disponibles >= p.cantidad_piezas:
                lot.cantidad_piezas_disponibles -= p.cantidad_piezas
                lot.cantidad_piezas_reservadas += p.cantidad_piezas

    quote.estado = "ANTICIPO_50_PAGADO"
    quote.mensaje_vigencia = "Anticipo 50% Pagado — Material Reservado en Piso Querétaro"
    return quote


def mass_update_steel_prices(
    store: MetaliaInMemoryStore,
    porcentaje_ajuste: Decimal,
) -> int:
    """
    HU-06: Actualiza masivamente el precio base por m² de todas las variantes del catálogo
    ante fluctuaciones del precio de la tonelada de acero o tipo de cambio.
    """
    factor = Decimal(1) + (porcentaje_ajuste / Decimal(100))
    count = 0
    for var in store.variantes.values():
        var.precio_base_m2_mxn = (var.precio_base_m2_mxn * factor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        count += 1
    return count


def recalculate_expired_quote(
    folio: str,
    store: MetaliaInMemoryStore,
    current_time: datetime | None = None,
) -> CotizacionProyecto:
    """
    HU-06: Recalcula una cotización expirada aplicando la lista de precios del acero vigente
    y renovando su vigencia por 72 horas hábiles adicionales.
    """
    if folio not in store.cotizaciones:
        raise KeyError(f"Folio no encontrado: {folio}")
    quote = store.cotizaciones[folio]
    now = current_time or datetime.now(UTC)

    for p in quote.partidas:
        if p.sku in store.variantes and p.area_m2_facturada > Decimal(0):
            var = store.variantes[p.sku]
            nuevo_importe = (p.area_m2_facturada * var.precio_base_m2_mxn).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            p.importe_mxn = nuevo_importe
            p.precio_unitario_mxn = (
                nuevo_importe / Decimal(p.cantidad_piezas)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    subtotal = sum((p.importe_mxn for p in quote.partidas), Decimal("0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = (subtotal * Decimal("0.16")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + iva).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    anticipo = (total * Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    quote.subtotal_mxn = subtotal
    quote.iva_mxn = iva
    quote.total_mxn = total
    quote.anticipo_50_mxn = anticipo
    quote.liquidacion_50_mxn = (total - anticipo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    quote.fecha_emision = now
    quote.fecha_vigencia = _add_business_hours(now, VIGENCIA_HORAS_HABILES)
    quote.estado = "ENVIADA"
    quote.mensaje_vigencia = "Cotización Recalculada y Vigente (72 horas hábiles)"
    quote.whatsapp_share_url = _build_whatsapp_url(
        quote.folio, quote.cliente_nombre, quote.total_mxn, quote.peso_bruto_total_ton
    )
    return quote
