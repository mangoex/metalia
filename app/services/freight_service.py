"""
Servicio de Fletes Nacionales (RN-10) — Matriz Fletes 2023 con 1,239 destinos en México.
Cálculo por metro lineal según espesor de panel o por tonelada para acanalados y accesorios.
"""

from __future__ import annotations

import json
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "fletes_nacional_2023.json"

_CACHE: dict[str, Any] | None = None


def _normalize_str(text: str) -> str:
    """Normaliza texto removiendo acentos y convirtiendo a minúsculas para búsqueda tolerante."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip().lower()


def _load_data() -> dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if not DATA_PATH.exists():
            return {"total_destinos": 0, "total_estados": 0, "estados": [], "destinos": []}
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


def get_freight_states() -> list[str]:
    """Retorna la lista de los estados con cobertura de flete nacional."""
    data = _load_data()
    return data.get("estados", [])


def get_destinations_for_state(estado: str) -> list[str]:
    """Retorna la lista de municipios/ciudades destino para un estado."""
    data = _load_data()
    norm_estado = _normalize_str(estado)
    results = []
    for d in data.get("destinos", []):
        if _normalize_str(d["estado"]) == norm_estado:
            results.append(d["destino"])
    return sorted(set(results))


def get_freight_destination(estado: str, municipio: str) -> dict[str, Any] | None:
    """Busca y retorna el registro de flete para un estado y municipio."""
    data = _load_data()
    norm_estado = _normalize_str(estado)
    norm_mun = _normalize_str(municipio)

    # 1. Búsqueda exacta normalizada
    for d in data.get("destinos", []):
        if _normalize_str(d["estado"]) == norm_estado and _normalize_str(d["destino"]) == norm_mun:
            return d

    # 2. Búsqueda por subcadena tolerante
    for d in data.get("destinos", []):
        if _normalize_str(d["estado"]) == norm_estado:
            d_norm = _normalize_str(d["destino"])
            if norm_mun in d_norm or d_norm in norm_mun:
                return d

    return None


def calculate_destination_freight(
    estado: str | None,
    municipio: str | None,
    tipo_aplicacion: str = "TECHO",
    espesor_pulg: str | None = None,
    longitud_total_ml: Decimal = Decimal(0),
    peso_total_kg: Decimal = Decimal(0),
) -> dict[str, Any]:
    """
    Calcula el costo de flete comercial hacia un municipio destino nacional (RN-10).
    - Para panel aislado: se aplica tarifa $/ml según espesor.
    - Para acanalados, losacero o accesorios: se aplica tarifa $/tonelada.
    """
    if not estado or not municipio or estado == "PATIO_QUERETARO":
        return {
            "estado": estado or "Querétaro",
            "destino": municipio or "Patio Querétaro",
            "costo_flete_mxn": Decimal("0.00"),
            "tarifa_unitaria": Decimal("0.00"),
            "metodo_calculo": "ENTREGA_EN_PATIO_QUERETARO",
        }

    dest = get_freight_destination(estado, municipio)
    if not dest:
        # Fallback a flete estimado por peso estándar
        costo_ton = Decimal("1500.00")
        flete = (peso_total_kg / Decimal("1000.0")) * costo_ton
        return {
            "estado": estado,
            "destino": municipio,
            "costo_flete_mxn": Decimal(str(round(float(flete), 2))),
            "tarifa_unitaria": costo_ton,
            "metodo_calculo": "ESTIMADO_FUERA_DE_MATRIZ",
        }

    costo_ton = Decimal(str(dest["costo_ton_mxn"]))

    # Si es panel con espesor reconocido en la matriz
    if espesor_pulg and longitud_total_ml > Decimal(0):
        tarifa_map = dest["techos_ml"] if tipo_aplicacion.upper() == "TECHO" else dest["muros_ml"]
        # Normalizar clave de espesor (ej. '1.5' -> '1.5"')
        clean_esp = espesor_pulg if '"' in espesor_pulg else f'{espesor_pulg}"'
        if clean_esp in tarifa_map and tarifa_map[clean_esp] > 0:
            tarifa_ml = Decimal(str(tarifa_map[clean_esp]))
            costo_total = (longitud_total_ml * tarifa_ml).quantize(Decimal("0.01"))
            return {
                "estado": dest["estado"],
                "destino": dest["destino"],
                "costo_flete_mxn": costo_total,
                "tarifa_unitaria": tarifa_ml,
                "metodo_calculo": "TARIFA_POR_METRO_LINEAL",
            }

    # Si es acanalado simple, losacero o accesorio, o espesor no mapeado en ml: cálculo por tonelada
    flete = ((peso_total_kg / Decimal("1000.0")) * costo_ton).quantize(Decimal("0.01"))
    return {
        "estado": dest["estado"],
        "destino": dest["destino"],
        "costo_flete_mxn": flete,
        "tarifa_unitaria": costo_ton,
        "metodo_calculo": "RECUPERACION_POR_TONELADA",
    }
