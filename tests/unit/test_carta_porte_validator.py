"""Pruebas unitarias para el Módulo Logístico y Pre-Validador de Complemento Carta Porte 3.1 (RN-09 y HU-07)."""

import re
from decimal import Decimal

import pytest


def test_hu07_carta_porte_31_exact_weight_validation_and_idccp(store):
    """
    HU-07 (Criterio Gherkin Exacto):
    Dado un pedido listo para entrega con peso calculado de 11,165 kg en paneles
    y 180 kg en accesorios,
    Cuando el usuario selecciona 'Generar Datos Carta Porte 3.1',
    Entonces:
    - Valida que PesoBrutoTotal (11,345 kg) coincida exactamente con la suma de las mercancías
    - Verifica los catálogos de códigos postales y permisos SCT (TPAF01)
    - Genera el payload JSON con IdCCP que inicia con 'CCC' bajo RFC 4122
    """
    from app.models.domain import CartaPorteMercanciaInput, CartaPorteRequest
    from app.services.logistics_carta_porte import build_and_validate_carta_porte_31

    req = CartaPorteRequest(
        folio_cotizacion="MET-CPQ-0001",
        modalidad_transporte="FLOTA_PROPIA_TRASLADO",
        codigo_postal_origen="76000",
        codigo_postal_destino="76220",
        permiso_sct="TPAF01",
        numero_permiso_sct="SCT-QRO-2026-9981",
        config_vehicular="T3S2",
        placa_vm="QRO458A",
        anio_modelo_vm=2024,
        subtipo_remolque="CTR021",
        placa_remolque="45TX9B",
        operador_nombre="Juan Pérez Hernández",
        operador_rfc="PEHJ850101ABC",
        operador_licencia="FED0019283",
        peso_bruto_total_declarado_kg=Decimal("11345.00"),
        mercancias=[
            CartaPorteMercanciaInput(
                bienes_transp_sat="30151500",
                descripcion="Panel Aislado Galvatecho 1.5 pulg Cal 26/26 Arena",
                cantidad=Decimal(160),
                clave_unidad_sat="H87",
                peso_en_kg=Decimal("11165.00"),
                largo_m=Decimal("6.33"),
            ),
            CartaPorteMercanciaInput(
                bienes_transp_sat="31161500",
                descripcion="Kit de Fijación Pijas, Clips Cal. 18 y Remates Pintro",
                cantidad=Decimal(1),
                clave_unidad_sat="XPK",
                peso_en_kg=Decimal("180.00"),
                largo_m=Decimal("3.05"),
            ),
        ],
    )

    payload = build_and_validate_carta_porte_31(req)

    assert payload["Version"] == "3.1"
    assert payload["TipoCFDI"] == "T"  # Traslado (flota propia)
    assert payload["TotalCFDI_MXN"] == "0.00"
    assert payload["Mercancias"]["PesoBrutoTotal"] == "11345.00"
    assert re.match(
        r"^CCC[0-9a-fA-F]{5}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        payload["IdCCP"],
    )
    assert payload["Autotransporte"]["PermSCT"] == "TPAF01"
    assert payload["Autotransporte"]["Remolques"][0]["SubTipoRem"] == "CTR021"


def test_rn09_carta_porte_rejects_mismatched_gross_weight():
    """
    RN-09: Si PesoBrutoTotal no coincide exactamente con la suma de PesoEnKg de las mercancías,
    el pre-validador debe rechazar la emisión antes de llamar al PAC para evitar multas del SAT.
    """
    from app.models.domain import CartaPorteMercanciaInput, CartaPorteRequest
    from app.services.logistics_carta_porte import build_and_validate_carta_porte_31

    req = CartaPorteRequest(
        folio_cotizacion="MET-CPQ-0002",
        modalidad_transporte="FLETERA_TERCERO_INGRESO",
        codigo_postal_origen="76000",
        codigo_postal_destino="37000",
        permiso_sct="TPAF01",
        numero_permiso_sct="SCT-GTO-2026-1122",
        config_vehicular="C3",
        placa_vm="GTO112B",
        anio_modelo_vm=2023,
        operador_nombre="Pedro Gómez",
        operador_rfc="GOPP800202XYZ",
        operador_licencia="FED998877",
        peso_bruto_total_declarado_kg=Decimal("5000.00"),  # Incorrecto vs 5240.00
        mercancias=[
            CartaPorteMercanciaInput(
                bienes_transp_sat="30151500",
                descripcion="Panel Multymuro 1.5 pulg",
                cantidad=Decimal(50),
                clave_unidad_sat="H87",
                peso_en_kg=Decimal("5240.00"),
                largo_m=Decimal("6.00"),
            )
        ],
    )

    with pytest.raises(ValueError, match="PesoBrutoTotal"):
        build_and_validate_carta_porte_31(req)
