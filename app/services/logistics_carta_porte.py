"""
Módulo Logístico, Dimensionamiento de Unidades de Transporte y Pre-Validador de Complemento Carta Porte 3.1 (RN-09, HU-07).
"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.models.domain import CartaPorteRequest

PERMISOS_SCT_VALIDOS = {"TPAF01", "TPAF02", "TPAF03", "TPXX00"}


def determine_transport_unit_and_freight(
    peso_total_kg: Decimal,
    largo_max_pieza_m: Decimal,
    codigo_postal_destino: str = "76000",
    tipo_entrega: str = "LAB_PATIO_QRO",
) -> tuple[str, Decimal]:
    """
    Determina la unidad de transporte requerida según largo máximo de pieza y tonelaje total,
    y calcula el costo de flete estimado desde el patio en Querétaro (CP 76000).
    """
    if largo_max_pieza_m <= Decimal("6.10") and peso_total_kg <= Decimal("3500.00"):
        unidad = "Camioneta 3.5 Toneladas (Plataforma 6.10 m)"
        tarifa_base = Decimal("3200.00")
    elif largo_max_pieza_m <= Decimal("8.00") and peso_total_kg <= Decimal("12000.00"):
        unidad = "Camión Rabón / Torton (Plataforma 8.00 m)"
        tarifa_base = Decimal("6800.00")
    else:
        unidad = "Plataforma de Tráiler 40 a 48 pies (12.20 m - 14.63 m)"
        tarifa_base = Decimal("12500.00")

    if tipo_entrega == "LAB_PATIO_QRO":
        return (f"{unidad} — Entrega LAB Patio Metalia Querétaro", Decimal("0.00"))

    # Factor regional según código postal (76xxx Querétaro metropolitano vs foráneo Bajío)
    cp_clean = (codigo_postal_destino or "76000").strip()
    if cp_clean.startswith("76"):
        factor_zona = Decimal("1.00")
    elif cp_clean.startswith(("36", "37", "38", "42", "58", "78")):  # Corredor Bajío / Centro
        factor_zona = Decimal("1.65")
    else:
        factor_zona = Decimal("2.25")

    costo_flete = (tarifa_base * factor_zona).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return (unidad, costo_flete)


def generate_id_ccp() -> str:
    """
    Genera el identificador IdCCP del Complemento Carta Porte 3.1 bajo estándar RFC 4122,
    donde los primeros tres caracteres deben ser obligatoriamente 'CCC'.
    """
    raw_uuid = str(uuid.uuid4())
    return "CCC" + raw_uuid[3:]


def build_and_validate_carta_porte_31(req: CartaPorteRequest) -> dict[str, Any]:
    """
    RN-09 / HU-07: Pre-valida determinísticamente el manifiesto de carga para el Complemento
    Carta Porte 3.1 antes de timbrar con el PAC (Fiscalapi / Facturama), previniendo rechazos
    y multas federales de $17,000 a $90,000 MXN:
    1. Valida que PesoBrutoTotal sea exactamente igual a la suma de PesoEnKg de todas las mercancías.
    2. Verifica formato de códigos postales de 5 dígitos.
    3. Verifica clave de permiso SCT (ej. TPAF01).
    4. Bifurca entre CFDI de Traslado ('T', total $0.00 para flota propia) y CFDI de Ingreso ('I', fletera tercera).
    """
    if not req.mercancias:
        raise ValueError("El manifiesto de Carta Porte 3.1 debe incluir al menos una mercancía.")

    suma_pesos_kg = sum(
        (m.peso_en_kg for m in req.mercancias), Decimal("0.00")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    declarado_kg = req.peso_bruto_total_declarado_kg.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if declarado_kg != suma_pesos_kg:
        raise ValueError(
            f"Error de pre-validación SAT Carta Porte 3.1: El atributo PesoBrutoTotal ({declarado_kg} kg) "
            f"no coincide con la suma exacta de PesoEnKg de las mercancías ({suma_pesos_kg} kg)."
        )

    if not (len(req.codigo_postal_origen) == 5 and req.codigo_postal_origen.isdigit()):
        raise ValueError(f"Código postal de origen inválido ante catálogo SAT: {req.codigo_postal_origen}")

    if not (len(req.codigo_postal_destino) == 5 and req.codigo_postal_destino.isdigit()):
        raise ValueError(f"Código postal de destino inválido ante catálogo SAT: {req.codigo_postal_destino}")

    if req.permiso_sct not in PERMISOS_SCT_VALIDOS:
        raise ValueError(f"Clave de permiso SCT no reconocida para carga federal: {req.permiso_sct}")

    es_traslado_propio = req.modalidad_transporte == "FLOTA_PROPIA_TRASLADO"
    tipo_cfdi = "T" if es_traslado_propio else "I"
    subtotal_cfdi = Decimal("0.00") if es_traslado_propio else req.monto_flete_mxn.quantize(Decimal("0.01"))
    total_cfdi = (
        Decimal("0.00")
        if es_traslado_propio
        else (subtotal_cfdi * Decimal("1.16")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )

    remolques_list = []
    if req.subtipo_remolque and req.placa_remolque:
        remolques_list.append(
            {
                "SubTipoRem": req.subtipo_remolque,
                "Placa": req.placa_remolque,
            }
        )

    return {
        "Version": "3.1",
        "IdCCP": generate_id_ccp(),
        "FolioCotizacionOrigen": req.folio_cotizacion,
        "TipoCFDI": tipo_cfdi,
        "ModalidadFiscal": (
            "CFDI de Traslado (Flota Propia Metalia)"
            if es_traslado_propio
            else "CFDI de Ingreso (Transportista Tercero)"
        ),
        "SubTotalCFDI_MXN": f"{subtotal_cfdi:.2f}",
        "TotalCFDI_MXN": f"{total_cfdi:.2f}",
        "TranspInternac": "No",
        "Ubicaciones": [
            {
                "TipoUbicacion": "Origen",
                "RFCRemitenteDestinatario": "MMS180412QRO",
                "NombreRemitenteDestinatario": "Metalia-MS, S.A. de C.V. (Patio Querétaro)",
                "Domicilio": {"CodigoPostal": req.codigo_postal_origen, "Estado": "QUE", "Pais": "MEX"},
            },
            {
                "TipoUbicacion": "Destino",
                "RFCRemitenteDestinatario": "XAXX010101000",
                "NombreRemitenteDestinatario": "Obra Cliente Destino",
                "Domicilio": {"CodigoPostal": req.codigo_postal_destino, "Pais": "MEX"},
            },
        ],
        "Mercancias": {
            "PesoBrutoTotal": f"{suma_pesos_kg:.2f}",
            "UnidadPeso": "KGM",
            "NumTotalMercancias": len(req.mercancias),
            "Mercancia": [
                {
                    "BienesTransp": m.bienes_transp_sat,
                    "Descripcion": m.descripcion,
                    "Cantidad": str(m.cantidad),
                    "ClaveUnidad": m.clave_unidad_sat,
                    "PesoEnKg": f"{m.peso_en_kg:.2f}",
                    "Dimensiones": f"{m.largo_m:.2f}m" if m.largo_m else "Estándar",
                }
                for m in req.mercancias
            ],
        },
        "Autotransporte": {
            "PermSCT": req.permiso_sct,
            "NumPermisoSCT": req.numero_permiso_sct,
            "IdentificacionVehicular": {
                "ConfigVehicular": req.config_vehicular,
                "PlacaVM": req.placa_vm,
                "AnioModeloVM": req.anio_modelo_vm,
                "PesoBrutoVehicularTon": f"{(suma_pesos_kg / Decimal(1000) + Decimal('7.5')):.2f}",
            },
            "Remolques": remolques_list,
        },
        "FiguraTransporte": [
            {
                "TipoFigura": "01",
                "RFCFigura": req.operador_rfc,
                "NumLicencia": req.operador_licencia,
                "NombreFigura": req.operador_nombre,
            }
        ],
    }
