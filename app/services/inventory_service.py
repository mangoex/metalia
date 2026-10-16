"""
Servicio de Inventario Dimensional en Piso, Órdenes de Corte y Control de Retazos (RN-05, HU-02, HU-05).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.models.domain import (
    CutOrderResult,
    InventarioDimensionalPiso,
    MetaliaInMemoryStore,
    StockAllocationResult,
)

LARGO_MINIMO_RETAZO_COMERCIAL_M = Decimal("2.00")
ALTURA_MAXIMA_ESTIBA_SEGURIDAD_M = Decimal("1.50")


def register_inventory_lot(
    store: MetaliaInMemoryStore,
    sku: str,
    largo_pieza_m: Decimal,
    cantidad_piezas: int,
    ubicacion_patio: str,
    altura_estiba_m: Decimal = Decimal("1.20"),
    admite_corte: bool = True,
    es_retazo: bool = False,
    lote_origen_id: str | None = None,
) -> InventarioDimensionalPiso:
    """
    Da de alta un lote físico en el almacén de Querétaro validando la norma técnica
    de seguridad de apilamiento (altura_estiba_m <= 1.50 m para no colapsar el núcleo de poliuretano).
    """
    if altura_estiba_m > ALTURA_MAXIMA_ESTIBA_SEGURIDAD_M:
        raise ValueError(
            f"Violación de seguridad industrial: La altura de estiba ({altura_estiba_m} m) "
            f"excede el máximo permitido de {ALTURA_MAXIMA_ESTIBA_SEGURIDAD_M} m."
        )
    store.get_variante(sku)
    lot = InventarioDimensionalPiso(
        id_lote=store.next_lot_id(),
        sku=sku,
        largo_pieza_m=largo_pieza_m.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        cantidad_piezas_disponibles=cantidad_piezas,
        admite_corte=admite_corte,
        es_retazo=es_retazo,
        lote_origen_id=lote_origen_id,
        ubicacion_patio=ubicacion_patio,
        altura_estiba_m=altura_estiba_m,
    )
    store.inventario_piso.append(lot)
    return lot


def evaluate_direct_line_stock(
    store: MetaliaInMemoryStore,
    sku: str,
    cantidad_piezas: int,
    largo_requerido_m: Decimal,
) -> StockAllocationResult:
    """
    RN-05: Evalúa la disponibilidad de una partida dimensional:
    1. Si la variante es Make-to-Order (es_estandar_en_piso=False) o largo > 12.20 m -> FABRICACION_PLANTA.
    2. Si existe lote con largo exacto y stock suficiente -> STOCK_EXACTO_PISO ('Disponible en Piso - Entrega Inmediata').
    3. Si existe lote mayor con corte habilitado -> CORTE_HOJA_MAESTRA:
       - Si sobrante < 2.00 m -> se factura el largo de la hoja comercial y no genera retazo.
       - Si sobrante >= 2.00 m -> se corta de hoja maestra y genera retazo comercializable.
    4. Si no hay existencias suficientes en patio -> FABRICACION_PLANTA.
    """
    var = store.get_variante(sku)
    fam = store.familias[var.familia_id]
    w_ef = fam.ancho_efectivo_m
    l_req = largo_requerido_m.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    area_neta = (Decimal(cantidad_piezas) * l_req * w_ef).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if not var.es_estandar_en_piso or l_req > Decimal("12.20"):
        peso_kg = (area_neta * var.peso_kg_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        importe = (area_neta * var.precio_base_m2_mxn).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return StockAllocationResult(
            sku=sku,
            cantidad_piezas=cantidad_piezas,
            largo_requerido_m=l_req,
            largo_facturado_m=l_req,
            ancho_efectivo_m=w_ef,
            area_m2_neta=area_neta,
            area_m2_facturada=area_neta,
            peso_total_kg=peso_kg,
            origen_suministro="FABRICACION_PLANTA",
            distintivo_disponibilidad="Fabricación Especial Bajo Pedido (Sujeto a tiempos de planta)",
            precio_m2_mxn=var.precio_base_m2_mxn,
            importe_mxn=importe,
        )

    # 1. Buscar match exacto en piso
    exact_lots = [
        lot
        for lot in store.inventario_piso
        if lot.sku == sku
        and lot.largo_pieza_m.quantize(Decimal("0.01")) == l_req
        and lot.cantidad_piezas_disponibles >= cantidad_piezas
    ]
    if exact_lots:
        chosen = exact_lots[0]
        peso_kg = (area_neta * var.peso_kg_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        importe = (area_neta * var.precio_base_m2_mxn).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return StockAllocationResult(
            sku=sku,
            cantidad_piezas=cantidad_piezas,
            largo_requerido_m=l_req,
            largo_facturado_m=l_req,
            largo_hoja_origen_m=chosen.largo_pieza_m,
            id_lote_asignado=chosen.id_lote,
            ancho_efectivo_m=w_ef,
            area_m2_neta=area_neta,
            area_m2_facturada=area_neta,
            peso_total_kg=peso_kg,
            origen_suministro="STOCK_EXACTO_PISO",
            distintivo_disponibilidad="Disponible en Piso - Entrega Inmediata",
            precio_m2_mxn=var.precio_base_m2_mxn,
            importe_mxn=importe,
        )

    # 2. Buscar hoja superior que admita corte ordenada ascendentemente por largo
    cuttable_lots = sorted(
        [
            lot
            for lot in store.inventario_piso
            if lot.sku == sku
            and lot.largo_pieza_m > l_req
            and lot.admite_corte
            and lot.cantidad_piezas_disponibles >= cantidad_piezas
        ],
        key=lambda x: x.largo_pieza_m,
    )
    if cuttable_lots:
        chosen = cuttable_lots[0]
        sobrante = (chosen.largo_pieza_m - l_req).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if sobrante < LARGO_MINIMO_RETAZO_COMERCIAL_M:
            # Merma invendible (< 2.00 m): se factura la medida comercial estándar inmediata superior
            largo_facturado = chosen.largo_pieza_m
            genera_retazo = False
            distintivo = (
                f"En Piso con Servicio de Corte desde hoja de {chosen.largo_pieza_m} m "
                f"(merma {sobrante} m < 2.00 m)"
            )
        else:
            # Hoja maestra con retazo comercializable (>= 2.00 m)
            largo_facturado = l_req
            genera_retazo = True
            distintivo = (
                f"En Piso con Corte de Hoja Maestra ({chosen.largo_pieza_m} m -> "
                f"retazo comercializable de {sobrante} m)"
            )

        area_facturada = (Decimal(cantidad_piezas) * largo_facturado * w_ef).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        peso_kg = (area_neta * var.peso_kg_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        importe = (area_facturada * var.precio_base_m2_mxn).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return StockAllocationResult(
            sku=sku,
            cantidad_piezas=cantidad_piezas,
            largo_requerido_m=l_req,
            largo_facturado_m=largo_facturado,
            largo_hoja_origen_m=chosen.largo_pieza_m,
            id_lote_asignado=chosen.id_lote,
            ancho_efectivo_m=w_ef,
            area_m2_neta=area_neta,
            area_m2_facturada=area_facturada,
            peso_total_kg=peso_kg,
            origen_suministro="CORTE_HOJA_MAESTRA",
            distintivo_disponibilidad=distintivo,
            merma_m=sobrante,
            genera_retazo_comercializable=genera_retazo,
            precio_m2_mxn=var.precio_base_m2_mxn,
            importe_mxn=importe,
        )

    # 3. Sin stock suficiente en patio -> Programación en Planta
    peso_kg = (area_neta * var.peso_kg_m2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    importe = (area_neta * var.precio_base_m2_mxn).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return StockAllocationResult(
        sku=sku,
        cantidad_piezas=cantidad_piezas,
        largo_requerido_m=l_req,
        largo_facturado_m=l_req,
        ancho_efectivo_m=w_ef,
        area_m2_neta=area_neta,
        area_m2_facturada=area_neta,
        peso_total_kg=peso_kg,
        origen_suministro="FABRICACION_PLANTA",
        distintivo_disponibilidad="Fabricación Especial Bajo Pedido (Sujeto a tiempos de planta)",
        precio_m2_mxn=var.precio_base_m2_mxn,
        importe_mxn=importe,
    )


def execute_cut_order(
    store: MetaliaInMemoryStore,
    id_lote_origen: str,
    cantidad_piezas: int,
    largo_corte_m: Decimal,
) -> CutOrderResult:
    """
    HU-05 / RN-05: Ejecuta una orden de corte sobre un lote en piso.
    Descuenta las hojas madre y, si el sobrante es >= 2.00 m, da de alta automáticamente
    un nuevo lote de retazo comercializable con es_retazo = True.
    """
    lote_origen = next(
        (lot for lot in store.inventario_piso if lot.id_lote == id_lote_origen),
        None,
    )
    if lote_origen is None:
        raise KeyError(f"Lote de origen no encontrado: {id_lote_origen}")
    if lote_origen.cantidad_piezas_disponibles < cantidad_piezas:
        raise ValueError(
            f"Stock insuficiente en lote {id_lote_origen}: disponibles "
            f"{lote_origen.cantidad_piezas_disponibles}, solicitadas {cantidad_piezas}."
        )
    if largo_corte_m >= lote_origen.largo_pieza_m:
        raise ValueError(
            f"El largo de corte ({largo_corte_m} m) debe ser menor al largo de la hoja ({lote_origen.largo_pieza_m} m)."
        )

    lote_origen.cantidad_piezas_disponibles -= cantidad_piezas
    sobrante = (lote_origen.largo_pieza_m - largo_corte_m).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    lote_retazo: InventarioDimensionalPiso | None = None
    genero_retazo = False
    if sobrante >= LARGO_MINIMO_RETAZO_COMERCIAL_M:
        genero_retazo = True
        lote_retazo = register_inventory_lot(
            store=store,
            sku=lote_origen.sku,
            largo_pieza_m=sobrante,
            cantidad_piezas=cantidad_piezas,
            ubicacion_patio=f"{lote_origen.ubicacion_patio}-RETAZOS",
            altura_estiba_m=Decimal("0.80"),
            admite_corte=True,
            es_retazo=True,
            lote_origen_id=lote_origen.id_lote,
        )

    res = CutOrderResult(
        id_orden_corte=store.next_cut_id(),
        id_lote_origen=lote_origen.id_lote,
        sku=lote_origen.sku,
        cantidad_cortada=cantidad_piezas,
        largo_corte_m=largo_corte_m.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        sobrante_m=sobrante,
        genero_retazo=genero_retazo,
        lote_retazo=lote_retazo,
    )
    store.ordenes_corte.append(res)
    return res
