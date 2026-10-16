"""Pruebas de integración E2E para la API REST y vistas web del Sistema CPQ Metalia."""

from fastapi.testclient import TestClient


def test_api_catalog_and_live_dimensional_inventory():
    """Verifica el endpoint de catálogo técnico e inventario dimensional en vivo en Querétaro."""
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/api/v1/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["familias"]) >= 6
    assert len(data["inventario_piso"]) >= 5


def test_api_preview_nave_and_evaluate_stock_endpoints():
    """Verifica los endpoints interactivos de previsualización geométrica/BOM y evaluación de stock."""
    from app.main import create_app

    client = TestClient(create_app())

    # 1. Preview de nave en tiempo real
    resp_prev = client.post(
        "/api/v1/cpq/preview-nave",
        json={
            "largo_nave_m": "30.0",
            "ancho_nave_m": "18.0",
            "altura_muro_m": "5.0",
            "aguas_techo": 1,
            "pendiente_pct": "6.0",
            "area_huecos_m2": "10.0",
            "alcance_obra": "NAVE_COMPLETA",
            "sku_cubierta": "LAMINA-KR18-24-PINTRO",
            "sku_muro": "MULTYMURO-15-2626-ARENA",
        },
    )
    assert resp_prev.status_code == 200
    prev_data = resp_prev.json()
    assert prev_data["geometria"]["tramos_por_vertiente"] == 2
    assert len(prev_data["bom"]["items"]) >= 4

    # 2. Preview con alcance SOLO_MUROS
    resp_muros = client.post(
        "/api/v1/cpq/preview-nave",
        json={
            "largo_nave_m": "20.0",
            "ancho_nave_m": "12.0",
            "altura_muro_m": "6.0",
            "aguas_techo": 2,
            "pendiente_pct": "5.0",
            "area_huecos_m2": "12.0",
            "alcance_obra": "SOLO_MUROS",
            "sku_cubierta": None,
            "sku_muro": "MULTYMURO-15-2626-ARENA",
        },
    )
    assert resp_muros.status_code == 200
    assert resp_muros.json()["geometria"]["piezas_totales_cubierta"] == 0
    assert resp_muros.json()["geometria"]["piezas_totales_muro"] > 0

    # 3. Evaluación de stock por línea directa
    resp_stock = client.post(
        "/api/v1/cpq/evaluate-stock",
        params={
            "sku": "MULTYMURO-15-2626-ARENA",
            "cantidad_piezas": 20,
            "largo_requerido_m": "6.00",
        },
    )
    assert resp_stock.status_code == 200
    assert resp_stock.json()["origen_suministro"] == "STOCK_EXACTO_PISO"


def test_api_direct_quote_cut_orders_and_steel_price_adjustment():
    """Verifica cotización directa (Modo A), órdenes de corte en patio y ajuste masivo del acero."""
    from app.main import create_app

    client = TestClient(create_app())

    # 1. Crear cotización en Modo Directo con instalación y flete
    res_dir = client.post(
        "/api/v1/quotes/direct",
        json={
            "cliente_nombre": "Ing. Laura Estrada",
            "cliente_empresa": "Agroindustrias del Bajío",
            "cliente_whatsapp": "4427778899",
            "cliente_email": "lestrada@agrobajio.mx",
            "codigo_postal_obra": "37000",
            "tipo_entrega": "FLETE_OBRA",
            "incluir_instalacion": True,
            "lineas": [
                {
                    "sku": "MULTYMURO-15-2626-ARENA",
                    "cantidad_piezas": 15,
                    "largo_pieza_m": "6.00",
                }
            ],
        },
    )
    assert res_dir.status_code == 200
    folio = res_dir.json()["folio"]

    # 2. Consultar cotización por folio
    res_get = client.get(f"/api/v1/quotes/{folio}")
    assert res_get.status_code == 200
    assert res_get.json()["folio"] == folio

    # 3. Ajuste masivo de precios del acero (+5%) y recálculo de cotización
    res_price = client.post(
        "/api/v1/admin/steel-price-adjustment",
        json={"porcentaje_ajuste": "5.0"},
    )
    assert res_price.status_code == 200
    assert res_price.json()["variantes_actualizadas"] >= 7

    res_recalc = client.post(f"/api/v1/quotes/{folio}/recalculate")
    assert res_recalc.status_code == 200
    assert float(res_recalc.json()["total_mxn"]) > float(res_dir.json()["total_mxn"])

    # 4. Ejecutar orden de corte sobre hoja maestra en patio (LOTE-QRO-0004 de 12.20 m -> corte 7.50 m)
    res_cut = client.post(
        "/api/v1/inventory/cut-orders",
        json={
            "id_lote_origen": "LOTE-QRO-0004",
            "cantidad_piezas": 3,
            "largo_corte_m": "7.50",
        },
    )
    assert res_cut.status_code == 200
    cut_json = res_cut.json()
    assert cut_json["genero_retazo"] is True
    assert cut_json["lote_retazo"]["largo_pieza_m"] == "4.70"
    assert cut_json["lote_retazo"]["es_retazo"] is True


def test_api_cpq_nave_calculation_and_carta_porte_flow():
    """Verifica el flujo completo: cálculo CPQ de nave -> cotización -> anticipo 50% -> Carta Porte 3.1."""
    from app.main import create_app

    client = TestClient(create_app())

    # 1. Crear cotización en modo Asistente Geométrico de Nave Industrial
    payload = {
        "cliente_nombre": "Ing. Fernando Alcántara",
        "cliente_empresa": "Parque Industrial El Marqués S.A.",
        "cliente_whatsapp": "4423334455",
        "cliente_email": "falcantara@elmarques.mx",
        "largo_nave_m": "40.0",
        "ancho_nave_m": "25.0",
        "altura_muro_m": "6.0",
        "aguas_techo": 2,
        "pendiente_pct": "5.0",
        "area_huecos_m2": "24.0",
        "alcance_obra": "NAVE_COMPLETA",
        "sku_cubierta": "GALVATECHO-15-2626-ARENA",
        "sku_muro": "MULTYMURO-15-2626-ARENA",
        "incluir_bom_accesorios": True,
        "incluir_estructura_polin": True,
        "incluir_instalacion": True,
        "codigo_postal_obra": "76246",
        "tipo_entrega": "FLETE_OBRA",
    }
    res_quote = client.post("/api/v1/quotes/nave", json=payload)
    assert res_quote.status_code == 200
    quote = res_quote.json()
    folio = quote["folio"]
    assert quote["estado"] == "ENVIADA"
    assert float(quote["peso_bruto_total_kg"]) > 10000.0

    # 2. Registrar pago del 50% de anticipo
    res_pay = client.post(f"/api/v1/quotes/{folio}/advance-payment")
    assert res_pay.status_code == 200
    assert res_pay.json()["estado"] == "ANTICIPO_50_PAGADO"

    # 3. Generar el payload pre-validado del Complemento Carta Porte 3.1 desde la cotización
    res_cp = client.post(
        f"/api/v1/quotes/{folio}/carta-porte",
        json={
            "modalidad_transporte": "FLOTA_PROPIA_TRASLADO",
            "permiso_sct": "TPAF01",
            "numero_permiso_sct": "SCT-QRO-2026-8842",
            "config_vehicular": "T3S2",
            "placa_vm": "QRO901X",
            "anio_modelo_vm": 2025,
            "subtipo_remolque": "CTR021",
            "placa_remolque": "99RM1A",
            "operador_nombre": "Miguel Ángel Torres",
            "operador_rfc": "TOMA820512QRO",
            "operador_licencia": "FED776655",
        },
    )
    assert res_cp.status_code == 200
    cp_data = res_cp.json()
    assert cp_data["Version"] == "3.1"
    assert cp_data["IdCCP"].startswith("CCC")
    assert cp_data["Mercancias"]["PesoBrutoTotal"] == str(quote["peso_bruto_total_kg"])


def test_web_ui_renders_accessible_cpq_portal():
    """Verifica que el portal principal renderice la interfaz accesible con el cotizador dual y el inventario."""
    from app.main import create_app

    client = TestClient(create_app())
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "Metalia" in html
    assert "Existencias en Piso Hoy en Querétaro" in html
    assert "Carta Porte 3.1" in html


def test_api_freight_endpoints_and_cascade_calculation():
    """Verifica los endpoints de flete nacional (estados, destinos, cálculo) y cascada comercial."""
    from app.main import create_app

    client = TestClient(create_app())

    # 1. Obtener estados
    res_est = client.get("/api/v1/fletes/estados")
    assert res_est.status_code == 200
    est_data = res_est.json()
    assert est_data["total"] >= 32
    assert "Sinaloa" in est_data["estados"]
    assert "Querétaro" in est_data["estados"]

    # 2. Obtener destinos para Sinaloa
    res_dest = client.get("/api/v1/fletes/destinos?estado=Sinaloa")
    assert res_dest.status_code == 200
    dest_data = res_dest.json()
    assert dest_data["total"] > 0
    assert any("Culiac" in d for d in dest_data["destinos"])

    # 3. Calcular flete por metro lineal (Panel Galvatecho 1.5" a Culiacán)
    res_calc_ml = client.post(
        "/api/v1/fletes/calculate",
        json={
            "estado": "Sinaloa",
            "municipio": "Culiacán",
            "tipo_aplicacion": "TECHO",
            "espesor_pulg": "1.5",
            "longitud_total_ml": "1012.80",
            "peso_total_kg": "10000.00",
        },
    )
    assert res_calc_ml.status_code == 200
    calc_ml = res_calc_ml.json()
    assert calc_ml["metodo_calculo"] == "TARIFA_POR_METRO_LINEAL"
    assert float(calc_ml["tarifa_unitaria"]) == 77.5619
    assert float(calc_ml["costo_flete_mxn"]) == 78554.69

    # 4. Calcular flete por tonelada (acanalados/accesorios a Monterrey)
    res_calc_ton = client.post(
        "/api/v1/fletes/calculate",
        json={
            "estado": "Nuevo León",
            "municipio": "Monterrey",
            "tipo_aplicacion": "TECHO",
            "espesor_pulg": None,
            "longitud_total_ml": "0.00",
            "peso_total_kg": "5000.00",
        },
    )
    assert res_calc_ton.status_code == 200
    calc_ton = res_calc_ton.json()
    assert calc_ton["metodo_calculo"] == "RECUPERACION_POR_TONELADA"
    assert float(calc_ton["costo_flete_mxn"]) > 0

    # 5. Calcular cascada comercial estándar
    res_casc = client.post(
        "/api/v1/pricing/cascade",
        json={
            "precio_lista_base_m2": "748.00",
            "es_espuma_fm": False,
            "descuento_planta_pct": "0.34",
            "indirecto_pct": "0.05",
            "margen_utilidad_pct": "0.25",
            "flete_unitario_m2": "77.56",
        },
    )
    assert res_casc.status_code == 200
    casc = res_casc.json()
    assert float(casc["costo_neto_compra_m2"]) == 493.68
    assert float(casc["costo_con_indirecto_m2"]) == 518.36
    assert float(casc["precio_venta_sin_flete_m2"]) == 647.95
    assert casc["alerta_margen_bajo"] is False

    # 6. Calcular cascada con espuma FM (+7%) y margen bajo (<15%)
    res_casc_fm = client.post(
        "/api/v1/pricing/cascade",
        json={
            "precio_lista_base_m2": "748.00",
            "es_espuma_fm": True,
            "descuento_planta_pct": "0.34",
            "indirecto_pct": "0.05",
            "margen_utilidad_pct": "0.10",  # Margen bajo
            "flete_unitario_m2": "0.00",
        },
    )
    assert res_casc_fm.status_code == 200
    casc_fm = res_casc_fm.json()
    assert float(casc_fm["precio_lista_ajustado_m2"]) == 800.36
    assert casc_fm["alerta_margen_bajo"] is True


def test_api_nave_quote_with_national_freight_and_cascade():
    """Verifica la creación de cotización CPQ con flete a Culiacán y desglose financiero."""
    from app.main import create_app

    client = TestClient(create_app())
    payload = {
        "cliente_nombre": "Agropecuario del Pacífico",
        "cliente_empresa": "Almacenes Culiacán",
        "cliente_whatsapp": "6671234567",
        "cliente_email": "ventas@almacenesculiacan.com",
        "largo_nave_m": "40.0",
        "ancho_nave_m": "25.0",
        "altura_muro_m": "6.0",
        "aguas_techo": 2,
        "pendiente_pct": "5.0",
        "area_huecos_m2": "24.0",
        "alcance_obra": "NAVE_COMPLETA",
        "sku_cubierta": "GALVATECHO-15-2626-ARENA",
        "sku_muro": "MULTYMURO-15-2626-ARENA",
        "porcentaje_luz_natural_pct": "10.0",
        "descuento_planta_pct": "0.34",
        "margen_utilidad_pct": "0.25",
        "es_espuma_fm": False,
        "estado_destino": "Sinaloa",
        "municipio_destino": "Culiacán",
        "tipo_entrega": "FLETE_OBRA",
    }
    res = client.post("/api/v1/quotes/nave", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["estado_destino"] == "Sinaloa"
    assert data["municipio_destino"] == "Culiacán"
    assert float(data["costo_total_material_mxn"]) > 0
    assert float(data["importe_venta_sin_flete_mxn"]) > 0
    assert float(data["utilidad_bruta_mxn"]) > 0
    assert float(data["margen_bruto_pct"]) >= 15.0
    assert data["alerta_margen_bajo"] is False
    # Validar que existan partidas de Acrylit G10 y flete
    skus = [p["sku"] for p in data["partidas"]]
    assert any("ACRYLIT" in sku for sku in skus)
    assert any("FLETE" in sku for sku in skus)
