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
