"""Pruebas unitarias para el Inventario Dimensional en Piso, Órdenes de Corte y Retazos (RN-05, HU-02, HU-05)."""

from decimal import Decimal

import pytest


def test_hu02_direct_despiece_multymuro_exact_stock_in_queretaro(store):
    """
    HU-02 (Criterio Gherkin Exacto):
    Dado que el usuario selecciona Multymuro 1.5'' Arena Cal. 26/26 (W_ef = 1.067 m)
    e ingresa 20 piezas de 6.00 m,
    Cuando el sistema consulta Inventario_Dimensional_Piso,
    Entonces:
    - Calcula 128.04 m2 (20 * 6.00 * 1.067)
    - Confirma que existen >= 20 piezas de 6.00 m en el almacén de Querétaro
    - Muestra el distintivo 'Disponible en Piso - Entrega Inmediata' (STOCK_EXACTO_PISO)
    """
    from app.services.inventory_service import evaluate_direct_line_stock

    allocation = evaluate_direct_line_stock(
        store=store,
        sku="MULTYMURO-15-2626-ARENA",
        cantidad_piezas=20,
        largo_requerido_m=Decimal("6.00"),
    )

    assert allocation.area_m2_facturada == Decimal("128.04")
    assert allocation.origen_suministro == "STOCK_EXACTO_PISO"
    assert allocation.distintivo_disponibilidad == "Disponible en Piso - Entrega Inmediata"
    assert allocation.largo_facturado_m == Decimal("6.00")


def test_hu05_master_sheet_cut_order_creates_remnant_lot_4_70m(store):
    """
    HU-05 (Criterio Gherkin Exacto):
    Dado un pedido pagado de 5 piezas de 7.50 m de Galvatecho 1.5'' que se surtirá
    cortando 5 hojas maestras de 12.20 m en piso,
    Cuando el almacén confirma la orden de corte,
    Entonces:
    - Descuenta 5 piezas del stock de 12.20 m
    - Da de alta automáticamente 5 piezas de retazo de 4.70 m en Inventario_Dimensional_Piso
      con etiqueta es_retazo = True
    """
    from app.services.inventory_service import execute_cut_order

    lote_maestro = store.find_lot(sku="GALVATECHO-15-2626-ARENA", largo_m=Decimal("12.20"))
    initial_available = lote_maestro.cantidad_piezas_disponibles

    cut_result = execute_cut_order(
        store=store,
        id_lote_origen=lote_maestro.id_lote,
        cantidad_piezas=5,
        largo_corte_m=Decimal("7.50"),
    )

    assert lote_maestro.cantidad_piezas_disponibles == initial_available - 5
    assert cut_result.genero_retazo is True
    assert cut_result.lote_retazo is not None
    assert cut_result.lote_retazo.largo_pieza_m == Decimal("4.70")
    assert cut_result.lote_retazo.cantidad_piezas_disponibles == 5
    assert cut_result.lote_retazo.es_retazo is True


def test_rn05_short_offcut_under_2m_charges_commercial_sheet_without_remnant(store):
    """
    RN-05: Si se solicita 7.50 m y se corta de una hoja de 8.00 m, el recorte de 0.50 m es < 2.00 m
    (invendible), por lo que se factura la hoja de 8.00 m y no se ingresa retazo comercializable.
    """
    from app.services.inventory_service import evaluate_direct_line_stock, execute_cut_order

    allocation = evaluate_direct_line_stock(
        store=store,
        sku="GALVATECHO-15-2626-ARENA",
        cantidad_piezas=4,
        largo_requerido_m=Decimal("7.50"),
    )
    assert allocation.origen_suministro == "CORTE_HOJA_MAESTRA"
    assert allocation.largo_hoja_origen_m == Decimal("8.00")
    assert allocation.largo_facturado_m == Decimal("8.00")
    assert allocation.merma_m == Decimal("0.50")
    assert allocation.genera_retazo_comercializable is False

    lote_8m = store.find_lot(sku="GALVATECHO-15-2626-ARENA", largo_m=Decimal("8.00"))
    cut_res = execute_cut_order(
        store=store,
        id_lote_origen=lote_8m.id_lote,
        cantidad_piezas=4,
        largo_corte_m=Decimal("7.50"),
    )
    assert cut_res.genero_retazo is False
    assert cut_res.lote_retazo is None


def test_rn05_special_thickness_triggers_make_to_order_plant(store):
    """
    RN-05: Espesores especiales de refrigeración (ej. 4.0'' o 5.0'') conmutan automáticamente a
    FABRICACION_PLANTA ('Fabricación Especial Bajo Pedido (Sujeto a tiempos de planta)').
    """
    from app.services.inventory_service import evaluate_direct_line_stock

    allocation = evaluate_direct_line_stock(
        store=store,
        sku="MULTYMURO-40-2626-BLANCO",
        cantidad_piezas=15,
        largo_requerido_m=Decimal("6.00"),
    )
    assert allocation.origen_suministro == "FABRICACION_PLANTA"
    assert "Fabricación Especial Bajo Pedido" in allocation.distintivo_disponibilidad


def test_rn05_stack_height_safety_limit_1_50m(store):
    """RN-05: Valida que no se permita registrar una estiba mayor a 1.50 m por seguridad del núcleo PU."""
    from app.services.inventory_service import register_inventory_lot

    with pytest.raises(ValueError, match="1.50"):
        register_inventory_lot(
            store=store,
            sku="GALVATECHO-15-2626-ARENA",
            largo_pieza_m=Decimal("6.00"),
            cantidad_piezas=20,
            ubicacion_patio="PATIO-A1",
            altura_estiba_m=Decimal("1.85"),
        )
