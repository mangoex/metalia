"""
Entidades nucleares del Modelo de Datos Dimensional de Metalia CPQ (SBD Sección 3.1):
1. ProductoFamilia (Catálogo Maestro)
2. VarianteTecnica (SKU Paramétrico)
3. InventarioDimensionalPiso (Stock Físico por Medida en Querétaro)
4. ReglaExplosionBOM (Motor de Accesorios e Instalación)
5. CotizacionProyecto y PartidaCotizacion (Folio CPQ y Máquina de Estados)
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field

MecanismoFijacion = Literal[
    "OCULTA_TAPAJUNTA",
    "EXPUESTA_TRASLAPE",
    "OCULTA_MURO",
    "ENGARGOLADA",
]

AlcanceObra = Literal["SOLO_TECHO", "SOLO_MUROS", "NAVE_COMPLETA"]

OrigenSuministro = Literal[
    "STOCK_EXACTO_PISO",
    "CORTE_HOJA_MAESTRA",
    "FABRICACION_PLANTA",
]

EstadoCotizacion = Literal[
    "BORRADOR",
    "ENVIADA",
    "EXPIRADA",
    "ANTICIPO_50_PAGADO",
    "EN_CORTE_O_PLANTA",
    "LISTA_EMBARQUE",
    "CARTA_PORTE_TIMBRADA",
    "ENTREGADA",
]


class ProductoFamilia(BaseModel):
    """Entidad 1: Catálogo Maestro de Familias de Producto."""

    id: str
    codigo_familia: str
    marca: str
    modelo: str
    mecanismo_fijacion: MecanismoFijacion
    ancho_efectivo_m: Decimal
    pendiente_minima_pct: Decimal = Decimal("5.0")
    largo_min_fabricacion_m: Decimal = Decimal("2.00")
    largo_max_plataforma_m: Decimal = Decimal("12.00")
    largo_max_linea_m: Decimal = Decimal("14.63")
    traslape_transversal_min_m: Decimal = Decimal("0.1524")
    desperdicio_default_pct: Decimal = Decimal("6.0")


class VarianteTecnica(BaseModel):
    """Entidad 2: SKU Paramétrico con propiedades físicas, térmicas y fiscales."""

    sku: str
    familia_id: str
    nombre_comercial: str
    espesor_pulg: Decimal | None = None
    calibre_ext_int: str
    acabado: str
    color: str
    tipo_espuma: str = "Poliuretano Alta Densidad (38-40 kg/m3)"
    peso_kg_m2: Decimal
    valor_r: Decimal = Decimal("0.00")
    factor_u: Decimal = Decimal("0.000")
    precio_base_m2_mxn: Decimal
    es_estandar_en_piso: bool = True
    lote_minimo_planta_m2: Decimal = Decimal("150.00")
    clave_prod_serv_sat: str = "30151500"
    clave_unidad_sat: str = "H87"


class InventarioDimensionalPiso(BaseModel):
    """Entidad 3: Lote físico de inventario por longitud en el patio de Querétaro."""

    id_lote: str
    sku: str
    largo_pieza_m: Decimal
    cantidad_piezas_disponibles: int
    cantidad_piezas_reservadas: int = 0
    admite_corte: bool = True
    es_retazo: bool = False
    lote_origen_id: str | None = None
    ubicacion_patio: str = "PATIO-QRO-A1"
    altura_estiba_m: Decimal = Decimal("1.20")


class ReglaExplosionBOM(BaseModel):
    """Entidad 4: Regla paramétrica de explosión de accesorios, fijación y remates."""

    id_regla: str
    tipo_regla: str
    sku_accesorio: str
    descripcion: str
    unidad: str
    largo_pieza_m: Decimal | None = None
    peso_unitario_kg: Decimal
    precio_unitario_mxn: Decimal
    clave_prod_serv_sat: str = "31161500"
    clave_unidad_sat: str = "H87"
    es_obligatorio: bool = True


class MolduraWizERP(BaseModel):
    """Moldura de Taller con código WizERP, desarrollo en cm y costo de habilitado (RN-15)."""

    codigo_wizerp: str
    descripcion: str
    desarrollo_cm: Decimal
    tiras_por_lamina: int
    costo_maquila_pza: Decimal
    costo_lamina_c22: Decimal = Decimal("756.06")
    costo_lamina_c24: Decimal = Decimal("564.64")

    @property
    def costo_unitario_habilitado(self) -> Decimal:
        if self.tiras_por_lamina <= 0:
            return self.costo_maquila_pza
        costo_tira = self.costo_lamina_c22 / Decimal(self.tiras_por_lamina)
        return (costo_tira + self.costo_maquila_pza).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SlopeFactorResult(BaseModel):
    """Resultado de RN-01: Factor trigonométrico de pendiente y alerta mínima."""

    pendiente_pct: Decimal
    factor_pendiente: Decimal
    alerta_pendiente_minima: bool
    mensaje_alerta: str


class NaveGeometryInput(BaseModel):
    """Parámetros de entrada para el Modo B (Asistente Geométrico de Nave Industrial)."""

    largo_nave_m: Decimal = Field(gt=Decimal(0))
    ancho_nave_m: Decimal = Field(gt=Decimal(0))
    altura_muro_m: Decimal = Field(default=Decimal("0.0"), ge=Decimal(0))
    aguas_techo: Literal[1, 2] = 2
    pendiente_pct: Decimal = Field(ge=Decimal(0))
    area_huecos_m2: Decimal = Field(default=Decimal("0.0"), ge=Decimal(0))
    alcance_obra: AlcanceObra = "NAVE_COMPLETA"
    sku_cubierta: str | None = "GALVATECHO-15-2626-ARENA"
    sku_muro: str | None = "MULTYMURO-15-2626-ARENA"
    desperdicio_cubierta_pct: Decimal = Decimal("6.0")
    desperdicio_muro_pct: Decimal = Decimal("6.0")
    rolado_en_sitio: bool = False
    porcentaje_luz_natural_pct: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("30.0"))
    descuento_planta_pct: Decimal = Field(default=Decimal("0.34"), ge=Decimal("0.0"), le=Decimal("0.60"))
    margen_utilidad_pct: Decimal = Field(default=Decimal("0.25"), ge=Decimal("0.05"), le=Decimal("0.70"))
    es_espuma_fm: bool = False
    estado_destino: str | None = None
    municipio_destino: str | None = None


class NaveGeometryResult(BaseModel):
    """Resultado del cálculo geométrico de cubierta y muros (RN-01 a RN-04, RN-14)."""

    factor_pendiente: Decimal
    alerta_pendiente_minima: bool
    mensaje_alerta_pendiente: str
    ancho_vertiente_m: Decimal
    largo_vertiente_m: Decimal
    supera_limite_plataforma: bool
    tramos_por_vertiente: int
    largo_tramo_cortado_m: Decimal
    traslape_transversal_m: Decimal
    ancho_efectivo_cubierta_m: Decimal
    hileras_por_agua: int
    hileras_totales_cubierta: int
    hileras_luz_natural: int = 0
    hileras_opacas: int = 0
    area_luz_natural_m2: Decimal = Decimal("0.00")
    piezas_totales_cubierta: int
    area_planta_m2: Decimal
    area_cubierta_real_m2: Decimal
    area_cubierta_con_desperdicio_m2: Decimal
    area_cubierta_facturada_m2: Decimal
    valor_r_cubierta: Decimal
    peso_cubierta_kg: Decimal
    peso_cubierta_ton: Decimal
    perimetro_m: Decimal
    area_muro_bruta_m2: Decimal
    area_muro_neta_m2: Decimal
    area_muro_con_desperdicio_m2: Decimal
    ancho_efectivo_muro_m: Decimal
    piezas_totales_muro: int
    area_muro_facturada_m2: Decimal
    peso_muro_kg: Decimal
    peso_muro_ton: Decimal
    peso_total_paneles_kg: Decimal
    peso_total_paneles_ton: Decimal


class BOMItemResult(BaseModel):
    """Partida generada por el motor de explosión de materiales (BOM)."""

    tipo_regla: str
    sku: str
    descripcion: str
    unidad: str
    cantidad: int
    largo_pieza_m: Decimal | None = None
    peso_unitario_kg: Decimal
    peso_total_kg: Decimal
    precio_unitario_mxn: Decimal
    importe_mxn: Decimal
    es_obligatorio: bool = True
    clave_prod_serv_sat: str = "31161500"
    clave_unidad_sat: str = "H87"


class BOMExplosionResult(BaseModel):
    """Resumen completo de la explosión BOM de accesorios, remates y polines."""

    items: list[BOMItemResult]
    peso_total_accesorios_kg: Decimal
    importe_total_accesorios_mxn: Decimal

    @property
    def partidas(self) -> list[BOMItemResult]:
        return self.items


class StockAllocationResult(BaseModel):
    """Resultado de evaluación de inventario dimensional en piso (RN-05)."""

    sku: str
    cantidad_piezas: int
    largo_requerido_m: Decimal
    largo_facturado_m: Decimal
    largo_hoja_origen_m: Decimal | None = None
    id_lote_asignado: str | None = None
    ancho_efectivo_m: Decimal
    area_m2_neta: Decimal
    area_m2_facturada: Decimal
    peso_total_kg: Decimal
    origen_suministro: OrigenSuministro
    distintivo_disponibilidad: str
    merma_m: Decimal = Decimal("0.00")
    genera_retazo_comercializable: bool = False
    precio_m2_mxn: Decimal
    importe_mxn: Decimal


class CutOrderResult(BaseModel):
    """Resultado de una orden de corte sobre hoja maestra en patio (HU-05)."""

    id_orden_corte: str
    id_lote_origen: str
    sku: str
    cantidad_cortada: int
    largo_corte_m: Decimal
    sobrante_m: Decimal
    genero_retazo: bool
    lote_retazo: InventarioDimensionalPiso | None = None


class PartidaCotizacion(BaseModel):
    """Entidad 5b: Línea de detalle dentro de una Cotización CPQ."""

    subsistema: str
    sku: str
    descripcion: str
    cantidad_piezas: int
    unidad: str = "PZA"
    largo_pieza_m: Decimal | None = None
    largo_facturado_m: Decimal | None = None
    area_m2_facturada: Decimal = Decimal("0.00")
    peso_partida_kg: Decimal = Decimal("0.00")
    origen_suministro: OrigenSuministro = "STOCK_EXACTO_PISO"
    distintivo_disponibilidad: str = "Disponible en Piso - Entrega Inmediata"
    precio_unitario_mxn: Decimal
    importe_mxn: Decimal
    clave_prod_serv_sat: str = "30151500"
    clave_unidad_sat: str = "H87"
    id_lote_reservable: str | None = None
    es_mercancia_fisica: bool = True


class CotizacionProyecto(BaseModel):
    """Entidad 5a: Cabecera de Cotización Formal (Folio CPQ)."""

    folio: str
    modo_captura: Literal["DIRECTO_DESPIECE", "GEOMETRICO_NAVE"]
    cliente_nombre: str
    cliente_empresa: str
    cliente_whatsapp: str
    cliente_email: str
    cliente_rfc: str = "XAXX010101000"
    codigo_postal_obra: str = "76000"
    tipo_entrega: Literal["LAB_PATIO_QRO", "FLETE_OBRA"] = "LAB_PATIO_QRO"
    estado: EstadoCotizacion = "ENVIADA"
    mensaje_vigencia: str = "Cotización Vigente (72 horas hábiles)"
    fecha_emision: datetime
    fecha_vigencia: datetime
    resumen_geometrico: NaveGeometryResult | None = None
    partidas: list[PartidaCotizacion]
    peso_bruto_total_kg: Decimal
    peso_bruto_total_ton: Decimal
    unidad_transporte_sugerida: str
    costo_total_material_mxn: Decimal = Decimal("0.00")
    importe_venta_sin_flete_mxn: Decimal = Decimal("0.00")
    utilidad_bruta_mxn: Decimal = Decimal("0.00")
    margen_bruto_pct: Decimal = Decimal("0.00")
    alerta_margen_bajo: bool = False
    estado_destino: str | None = None
    municipio_destino: str | None = None
    es_espuma_fm: bool = False
    subtotal_mxn: Decimal
    iva_mxn: Decimal
    total_mxn: Decimal
    anticipo_50_mxn: Decimal
    liquidacion_50_mxn: Decimal
    whatsapp_share_url: str


class DirectLineInput(BaseModel):
    """Línea de entrada para el Modo A (Cotizador Directo por Despiece)."""

    sku: str
    cantidad_piezas: int = Field(gt=0)
    largo_pieza_m: Decimal = Field(ge=Decimal("2.00"), le=Decimal("14.63"))


class CreateDirectQuoteRequest(BaseModel):
    """Solicitud para generar cotización en Modo Directo (HU-02)."""

    cliente_nombre: str
    cliente_empresa: str
    cliente_whatsapp: str
    cliente_email: str
    cliente_rfc: str = "XAXX010101000"
    codigo_postal_obra: str = "76000"
    tipo_entrega: Literal["LAB_PATIO_QRO", "FLETE_OBRA"] = "LAB_PATIO_QRO"
    incluir_instalacion: bool = False
    lineas: list[DirectLineInput]
    fecha_emision_override: datetime | None = None


class CreateNaveQuoteRequest(BaseModel):
    """Solicitud para generar cotización en Modo Proyecto / Nave Industrial (HU-01, HU-03, HU-04, HU-08..HU-10)."""

    cliente_nombre: str
    cliente_empresa: str
    cliente_whatsapp: str
    cliente_email: str
    cliente_rfc: str = "XAXX010101000"
    largo_nave_m: Decimal = Field(gt=Decimal(0))
    ancho_nave_m: Decimal = Field(gt=Decimal(0))
    altura_muro_m: Decimal = Field(default=Decimal("0.0"), ge=Decimal(0))
    aguas_techo: Literal[1, 2] = 2
    pendiente_pct: Decimal = Field(ge=Decimal(0))
    area_huecos_m2: Decimal = Field(default=Decimal("0.0"), ge=Decimal(0))
    alcance_obra: AlcanceObra = "NAVE_COMPLETA"
    sku_cubierta: str | None = "GALVATECHO-15-2626-ARENA"
    sku_muro: str | None = "MULTYMURO-15-2626-ARENA"
    desperdicio_cubierta_pct: Decimal = Decimal("6.0")
    desperdicio_muro_pct: Decimal = Decimal("6.0")
    porcentaje_luz_natural_pct: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), le=Decimal("30.0"))
    descuento_planta_pct: Decimal = Field(default=Decimal("0.34"), ge=Decimal("0.0"), le=Decimal("0.60"))
    margen_utilidad_pct: Decimal = Field(default=Decimal("0.25"), ge=Decimal("0.05"), le=Decimal("0.70"))
    es_espuma_fm: bool = False
    estado_destino: str | None = None
    municipio_destino: str | None = None
    incluir_bom_accesorios: bool = True
    incluir_estructura_polin: bool = False
    incluir_instalacion: bool = False
    codigo_postal_obra: str = "76000"
    tipo_entrega: Literal["LAB_PATIO_QRO", "FLETE_OBRA"] = "LAB_PATIO_QRO"
    fecha_emision_override: datetime | None = None


class CartaPorteMercanciaInput(BaseModel):
    """Mercancía individual para el Complemento Carta Porte 3.1."""

    bienes_transp_sat: str
    descripcion: str
    cantidad: Decimal
    clave_unidad_sat: str
    peso_en_kg: Decimal
    largo_m: Decimal | None = None


class CartaPorteRequest(BaseModel):
    """Solicitud de validación y generación del Complemento Carta Porte 3.1 (HU-07, RN-09)."""

    folio_cotizacion: str
    modalidad_transporte: Literal["FLOTA_PROPIA_TRASLADO", "FLETERA_TERCERO_INGRESO"] = (
        "FLOTA_PROPIA_TRASLADO"
    )
    codigo_postal_origen: str = "76000"
    codigo_postal_destino: str = "76220"
    permiso_sct: str = "TPAF01"
    numero_permiso_sct: str
    config_vehicular: str = "T3S2"
    placa_vm: str
    anio_modelo_vm: int = 2024
    subtipo_remolque: str | None = None
    placa_remolque: str | None = None
    operador_nombre: str
    operador_rfc: str
    operador_licencia: str
    monto_flete_mxn: Decimal = Decimal("0.00")
    peso_bruto_total_declarado_kg: Decimal
    mercancias: list[CartaPorteMercanciaInput]


class MetaliaInMemoryStore:
    """Almacén transaccional en memoria con el catálogo e inventario dimensional de Metalia Querétaro."""

    def __init__(self) -> None:
        self.familias: dict[str, ProductoFamilia] = {}
        self.variantes: dict[str, VarianteTecnica] = {}
        self.inventario_piso: list[InventarioDimensionalPiso] = []
        self.cotizaciones: dict[str, CotizacionProyecto] = {}
        self.ordenes_corte: list[CutOrderResult] = []
        self.molduras_wizerp: list[MolduraWizERP] = []
        self._quote_seq: int = 1
        self._cut_seq: int = 1
        self._lot_seq: int = 100

    def next_folio(self) -> str:
        folio = f"MET-QRO-{self._quote_seq:04d}"
        self._quote_seq += 1
        return folio

    def next_cut_id(self) -> str:
        cid = f"CORTE-{self._cut_seq:04d}"
        self._cut_seq += 1
        return cid

    def next_lot_id(self) -> str:
        lid = f"LOTE-QRO-{self._lot_seq:04d}"
        self._lot_seq += 1
        return lid

    def get_variante(self, sku: str) -> VarianteTecnica:
        if sku not in self.variantes:
            raise KeyError(f"SKU no encontrado en catálogo Metalia: {sku}")
        return self.variantes[sku]

    def get_familia_for_sku(self, sku: str) -> ProductoFamilia:
        var = self.get_variante(sku)
        return self.familias[var.familia_id]

    def find_lot(self, sku: str, largo_m: Decimal) -> InventarioDimensionalPiso:
        target = largo_m.quantize(Decimal("0.01"))
        for lot in self.inventario_piso:
            if lot.sku == sku and lot.largo_pieza_m.quantize(Decimal("0.01")) == target:
                return lot
        raise KeyError(f"No se encontró lote en piso para {sku} de {largo_m} m")


def create_default_metalia_store() -> MetaliaInMemoryStore:
    """Inicializa el catálogo técnico real (Ternium / Metecno) y el inventario en piso en Querétaro."""
    store = MetaliaInMemoryStore()

    familias = [
        ProductoFamilia(
            id="FAM-MULTYTECHO",
            codigo_familia="PANEL_TECHO",
            marca="Ternium",
            modelo="Multytecho",
            mecanismo_fijacion="OCULTA_TAPAJUNTA",
            ancho_efectivo_m=Decimal("1.000"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.50"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("14.63"),
            traslape_transversal_min_m=Decimal("0.200"),
            desperdicio_default_pct=Decimal("6.0"),
        ),
        ProductoFamilia(
            id="FAM-GALVATECHO",
            codigo_familia="PANEL_TECHO",
            marca="Ternium / Metecno",
            modelo="Galvatecho / Glamet G3",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("1.000"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("14.63"),
            traslape_transversal_min_m=Decimal("0.1524"),
            desperdicio_default_pct=Decimal("6.0"),
        ),
        ProductoFamilia(
            id="FAM-ECONOTECHO",
            codigo_familia="PANEL_TECHO",
            marca="Ternium / Metecno",
            modelo="Econotecho / Glamet LV",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("1.000"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.50"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.1524"),
            desperdicio_default_pct=Decimal("6.0"),
        ),
        ProductoFamilia(
            id="FAM-MULTYMURO",
            codigo_familia="PANEL_MURO",
            marca="Ternium / Metecno",
            modelo="Multymuro / Superwall",
            mecanismo_fijacion="OCULTA_MURO",
            ancho_efectivo_m=Decimal("1.067"),
            pendiente_minima_pct=Decimal("0.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.000"),
            desperdicio_default_pct=Decimal("6.0"),
        ),
        ProductoFamilia(
            id="FAM-LAMINA-R101",
            codigo_familia="LAMINA_ACANALADA",
            marca="Ternium",
            modelo="Lámina Trapezoidal R-101",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("1.016"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.200"),
            desperdicio_default_pct=Decimal("10.0"),
        ),
        ProductoFamilia(
            id="FAM-LAMINA-KR18",
            codigo_familia="LAMINA_KR18",
            marca="Ternium",
            modelo="Sistema Engargolado KR-18",
            mecanismo_fijacion="ENGARGOLADA",
            ancho_efectivo_m=Decimal("0.914"),
            pendiente_minima_pct=Decimal("3.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("60.00"),
            traslape_transversal_min_m=Decimal("0.000"),
            desperdicio_default_pct=Decimal("10.0"),
        ),
        ProductoFamilia(
            id="FAM-GALVATEJA",
            codigo_familia="LAMINA_TEJA",
            marca="Ternium / Metecno",
            modelo="Galvateja / Metcoppo",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("0.900"),
            pendiente_minima_pct=Decimal("12.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.150"),
            desperdicio_default_pct=Decimal("10.0"),
        ),
        ProductoFamilia(
            id="LOSACERO_25",
            codigo_familia="ENTREPISO_LOSACERO",
            marca="Ternium",
            modelo="Losacero 25",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("0.9144"),
            pendiente_minima_pct=Decimal("0.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.000"),
            desperdicio_default_pct=Decimal("5.0"),
        ),
        ProductoFamilia(
            id="TR_101",
            codigo_familia="LAMINA_ACANALADA",
            marca="Ternium",
            modelo="Lámina Trapezoidal TR-101",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("1.008"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.200"),
            desperdicio_default_pct=Decimal("10.0"),
        ),
        ProductoFamilia(
            id="TR_72",
            codigo_familia="LAMINA_ACANALADA",
            marca="Ternium",
            modelo="Lámina Ondulada TR-72",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("0.720"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.200"),
            desperdicio_default_pct=Decimal("10.0"),
        ),
        ProductoFamilia(
            id="ACRYLIT_G10",
            codigo_familia="TRANSLUCIDO",
            marca="Stabilit",
            modelo="Lámina Translúcida Acrylit G10",
            mecanismo_fijacion="EXPUESTA_TRASLAPE",
            ancho_efectivo_m=Decimal("1.000"),
            pendiente_minima_pct=Decimal("5.0"),
            largo_min_fabricacion_m=Decimal("2.00"),
            largo_max_plataforma_m=Decimal("12.00"),
            largo_max_linea_m=Decimal("12.00"),
            traslape_transversal_min_m=Decimal("0.200"),
            desperdicio_default_pct=Decimal("6.0"),
        ),
    ]
    for fam in familias:
        store.familias[fam.id] = fam

    variantes = [
        VarianteTecnica(
            sku="GALVATECHO-15-2626-ARENA",
            familia_id="FAM-GALVATECHO",
            nombre_comercial="Panel Galvatecho / Glamet 1.5'' Cal. 26/26 Arena Pintro",
            espesor_pulg=Decimal("1.5"),
            calibre_ext_int="26/26",
            acabado="Pintro Poliéster Estándar",
            color="Arena Estándar",
            peso_kg_m2=Decimal("10.45"),
            valor_r=Decimal("10.00"),
            factor_u=Decimal("0.100"),
            precio_base_m2_mxn=Decimal("645.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="GALVATECHO-20-2626-ARENA",
            familia_id="FAM-GALVATECHO",
            nombre_comercial="Panel Galvatecho / Glamet 2.0'' Cal. 26/26 Arena Pintro",
            espesor_pulg=Decimal("2.0"),
            calibre_ext_int="26/26",
            acabado="Pintro Poliéster Estándar",
            color="Arena Estándar",
            peso_kg_m2=Decimal("10.99"),
            valor_r=Decimal("13.33"),
            factor_u=Decimal("0.075"),
            precio_base_m2_mxn=Decimal("715.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="MULTYTECHO-15-2626-BLANCO",
            familia_id="FAM-MULTYTECHO",
            nombre_comercial="Panel Multytecho 1.5'' Cal. 26/26 Blanco Estándar (Fijación Oculta)",
            espesor_pulg=Decimal("1.5"),
            calibre_ext_int="26/26",
            acabado="Pintro Poliéster Estándar",
            color="Blanco Estándar",
            peso_kg_m2=Decimal("10.52"),
            valor_r=Decimal("10.50"),
            factor_u=Decimal("0.095"),
            precio_base_m2_mxn=Decimal("695.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="ECONOTECHO-15-26-BLANCO",
            familia_id="FAM-ECONOTECHO",
            nombre_comercial="Panel Econotecho / Glamet LV 1.5'' Cal. 26 / Vinil Blanco",
            espesor_pulg=Decimal("1.5"),
            calibre_ext_int="26/Vinil",
            acabado="Pintro / Película Vinil Interior",
            color="Blanco",
            peso_kg_m2=Decimal("6.80"),
            valor_r=Decimal("9.80"),
            factor_u=Decimal("0.102"),
            precio_base_m2_mxn=Decimal("525.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="MULTYMURO-15-2626-ARENA",
            familia_id="FAM-MULTYMURO",
            nombre_comercial="Panel Multymuro / Superwall 1.5'' Cal. 26/26 Arena (Ancho 1.067 m)",
            espesor_pulg=Decimal("1.5"),
            calibre_ext_int="26/26",
            acabado="Pintro Embozado con Ribs",
            color="Arena Estándar",
            peso_kg_m2=Decimal("10.30"),
            valor_r=Decimal("10.20"),
            factor_u=Decimal("0.098"),
            precio_base_m2_mxn=Decimal("660.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="MULTYMURO-20-2626-ARENA",
            familia_id="FAM-MULTYMURO",
            nombre_comercial="Panel Multymuro / Superwall 2.0'' Cal. 26/26 Arena (Ancho 1.067 m)",
            espesor_pulg=Decimal("2.0"),
            calibre_ext_int="26/26",
            acabado="Pintro Embozado con Ribs",
            color="Arena Estándar",
            peso_kg_m2=Decimal("11.10"),
            valor_r=Decimal("13.50"),
            factor_u=Decimal("0.074"),
            precio_base_m2_mxn=Decimal("735.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="MULTYMURO-40-2626-BLANCO",
            familia_id="FAM-MULTYMURO",
            nombre_comercial="Panel Multymuro Frigorífico 4.0'' Cal. 26/26 Blanco Clase 1 FM",
            espesor_pulg=Decimal("4.0"),
            calibre_ext_int="26/26",
            acabado="Pintro Duraplus Antimicrobiano",
            color="Blanco Frigorífico",
            tipo_espuma="Espuma Clase 1 FM (Cámara de Congelación)",
            peso_kg_m2=Decimal("13.85"),
            valor_r=Decimal("28.50"),
            factor_u=Decimal("0.035"),
            precio_base_m2_mxn=Decimal("1190.00"),
            es_estandar_en_piso=False,  # Fabricación especial en planta
            lote_minimo_planta_m2=Decimal("250.00"),
        ),
        VarianteTecnica(
            sku="LAMINA-R101-26-ZINTROALUM",
            familia_id="FAM-LAMINA-R101",
            nombre_comercial="Lámina Acanalada R-101 Cal. 26 Zintro Alum (Ancho útil 1.016 m)",
            espesor_pulg=None,
            calibre_ext_int="26",
            acabado="Zintro Alum",
            color="Aluminizado",
            tipo_espuma="Sin núcleo (Acero simple)",
            peso_kg_m2=Decimal("4.82"),
            valor_r=Decimal("0.50"),
            factor_u=Decimal("2.000"),
            precio_base_m2_mxn=Decimal("245.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="LAMINA-KR18-24-PINTRO",
            familia_id="FAM-LAMINA-KR18",
            nombre_comercial="Lámina Engargolable KR-18 Cal. 24 Pintro Blanco (Ancho útil 0.914 m)",
            espesor_pulg=None,
            calibre_ext_int="24",
            acabado="Pintro Poliéster",
            color="Blanco",
            tipo_espuma="Sin núcleo / Compatible con MBI",
            peso_kg_m2=Decimal("6.45"),
            valor_r=Decimal("0.60"),
            factor_u=Decimal("1.660"),
            precio_base_m2_mxn=Decimal("330.00"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="GALVATECHO-26-28-15-PIN",
            familia_id="FAM-GALVATECHO",
            nombre_comercial="Panel Galvatecho 1.5'' Cal. 26/28 Pintro / Pintro",
            espesor_pulg=Decimal("1.5"),
            calibre_ext_int="26/28",
            acabado="Pintro / Pintro",
            color="Blanco / Arena",
            peso_kg_m2=Decimal("10.52"),
            valor_r=Decimal("10.00"),
            factor_u=Decimal("0.100"),
            precio_base_m2_mxn=Decimal("706.82"),
            es_estandar_en_piso=True,
        ),
        VarianteTecnica(
            sku="LOSACERO-25-CAL22-GAL",
            familia_id="LOSACERO_25",
            nombre_comercial="Entrepiso Metálico Losacero 25 Calibre 22 Galvanizada",
            espesor_pulg=Decimal("2.5"),
            calibre_ext_int="22",
            acabado="Galvanizado G-90",
            color="Zintro",
            tipo_espuma="Sin Núcleo",
            peso_kg_m2=Decimal("8.20"),
            precio_base_m2_mxn=Decimal("347.68"),
            es_estandar_en_piso=True,
            clave_prod_serv_sat="30101700",
            clave_unidad_sat="H87",
        ),
        VarianteTecnica(
            sku="TR-101-CAL26-PNT",
            familia_id="TR_101",
            nombre_comercial="Lámina Acanalada TR-101 Calibre 26 Pintro",
            espesor_pulg=None,
            calibre_ext_int="26",
            acabado="Pintro Poliéster Estándar / Fondo",
            color="Blanco",
            tipo_espuma="Sin Núcleo",
            peso_kg_m2=Decimal("4.89"),
            precio_base_m2_mxn=Decimal("217.10"),
            es_estandar_en_piso=True,
            clave_prod_serv_sat="30151500",
            clave_unidad_sat="H87",
        ),
        VarianteTecnica(
            sku="TR-72-CAL26-ZIN",
            familia_id="TR_72",
            nombre_comercial="Lámina Acanalada TR-72 Calibre 26 Zintro",
            espesor_pulg=None,
            calibre_ext_int="26",
            acabado="Ternium Zintro",
            color="Galvanizado",
            tipo_espuma="Sin Núcleo",
            peso_kg_m2=Decimal("4.89"),
            precio_base_m2_mxn=Decimal("165.97"),
            es_estandar_en_piso=True,
            clave_prod_serv_sat="30151500",
            clave_unidad_sat="H87",
        ),
        VarianteTecnica(
            sku="ACRYLIT-G10-BLANCO",
            familia_id="ACRYLIT_G10",
            nombre_comercial="Lámina Translúcida Acrylit G10 Blanco Lechoso T-81",
            espesor_pulg=None,
            calibre_ext_int="1.4 mm",
            acabado="GelCoat Anti-UV",
            color="Blanco Lechoso",
            tipo_espuma="100% Resina Acrílica Reforzada con Fibra de Vidrio",
            peso_kg_m2=Decimal("2.50"),
            precio_base_m2_mxn=Decimal("391.11"),
            es_estandar_en_piso=True,
            clave_prod_serv_sat="30151500",
            clave_unidad_sat="H87",
        ),
    ]
    for var in variantes:
        store.variantes[var.sku] = var

    # Inventario físico en piso hoy en Querétaro (largos estándar y hojas maestras de 12.20 m)
    store.inventario_piso = [
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0001",
            sku="GALVATECHO-15-2626-ARENA",
            largo_pieza_m=Decimal("6.00"),
            cantidad_piezas_disponibles=45,
            admite_corte=False,
            ubicacion_patio="NAVE-1-A1",
            altura_estiba_m=Decimal("1.20"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0002",
            sku="GALVATECHO-15-2626-ARENA",
            largo_pieza_m=Decimal("8.00"),
            cantidad_piezas_disponibles=30,
            admite_corte=True,
            ubicacion_patio="NAVE-1-A2",
            altura_estiba_m=Decimal("1.30"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0003",
            sku="GALVATECHO-15-2626-ARENA",
            largo_pieza_m=Decimal("10.00"),
            cantidad_piezas_disponibles=25,
            admite_corte=True,
            ubicacion_patio="NAVE-1-A3",
            altura_estiba_m=Decimal("1.10"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0004",
            sku="GALVATECHO-15-2626-ARENA",
            largo_pieza_m=Decimal("12.20"),
            cantidad_piezas_disponibles=40,
            admite_corte=True,
            ubicacion_patio="NAVE-1-MAESTRA",
            altura_estiba_m=Decimal("1.40"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0005",
            sku="GALVATECHO-20-2626-ARENA",
            largo_pieza_m=Decimal("12.20"),
            cantidad_piezas_disponibles=28,
            admite_corte=True,
            ubicacion_patio="NAVE-1-B1",
            altura_estiba_m=Decimal("1.35"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0006",
            sku="MULTYTECHO-15-2626-BLANCO",
            largo_pieza_m=Decimal("6.00"),
            cantidad_piezas_disponibles=32,
            admite_corte=False,
            ubicacion_patio="NAVE-2-A1",
            altura_estiba_m=Decimal("1.15"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0007",
            sku="MULTYTECHO-15-2626-BLANCO",
            largo_pieza_m=Decimal("12.20"),
            cantidad_piezas_disponibles=35,
            admite_corte=True,
            ubicacion_patio="NAVE-2-MAESTRA",
            altura_estiba_m=Decimal("1.45"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0008",
            sku="MULTYMURO-15-2626-ARENA",
            largo_pieza_m=Decimal("5.00"),
            cantidad_piezas_disponibles=30,
            admite_corte=False,
            ubicacion_patio="NAVE-3-M1",
            altura_estiba_m=Decimal("1.20"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0009",
            sku="MULTYMURO-15-2626-ARENA",
            largo_pieza_m=Decimal("6.00"),
            cantidad_piezas_disponibles=50,
            admite_corte=False,
            ubicacion_patio="NAVE-3-M2",
            altura_estiba_m=Decimal("1.25"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0010",
            sku="MULTYMURO-15-2626-ARENA",
            largo_pieza_m=Decimal("12.00"),
            cantidad_piezas_disponibles=25,
            admite_corte=True,
            ubicacion_patio="NAVE-3-MAESTRA",
            altura_estiba_m=Decimal("1.30"),
        ),
        InventarioDimensionalPiso(
            id_lote="LOTE-QRO-0011",
            sku="LAMINA-R101-26-ZINTROALUM",
            largo_pieza_m=Decimal("6.10"),
            cantidad_piezas_disponibles=120,
            admite_corte=False,
            ubicacion_patio="PATIO-LAM-01",
            altura_estiba_m=Decimal("0.90"),
        ),
    ]

    store.molduras_wizerp = [
        MolduraWizERP(
            codigo_wizerp="CIIPFC2215305152",
            descripcion="CANAL INFERIOR INTERIOR 1 1/2\"",
            desarrollo_cm=Decimal("15.1"),
            tiras_por_lamina=8,
            costo_maquila_pza=Decimal("55.00"),
            costo_lamina_c22=Decimal("756.06"),
        ),
        MolduraWizERP(
            codigo_wizerp="CIIPFC2220305174",
            descripcion="CANAL INFERIOR INTERIOR 2\"",
            desarrollo_cm=Decimal("17.4"),
            tiras_por_lamina=7,
            costo_maquila_pza=Decimal("55.00"),
            costo_lamina_c22=Decimal("756.06"),
        ),
        MolduraWizERP(
            codigo_wizerp="TGPFC24305244",
            descripcion="TAPAGOTERO STD",
            desarrollo_cm=Decimal("24.4"),
            tiras_por_lamina=5,
            costo_maquila_pza=Decimal("70.00"),
            costo_lamina_c24=Decimal("564.64"),
        ),
        MolduraWizERP(
            codigo_wizerp="CABALLETE_LISO",
            descripcion="CABALLETE CENTRAL CUMBRERA 3.05M",
            desarrollo_cm=Decimal("40.0"),
            tiras_por_lamina=3,
            costo_maquila_pza=Decimal("80.00"),
            costo_lamina_c22=Decimal("756.06"),
        ),
    ]

    return store
