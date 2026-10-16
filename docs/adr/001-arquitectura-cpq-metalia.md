# ADR-001: Arquitectura del Sistema Web CPQ, Explosión BOM, Inventario Dimensional y Carta Porte 3.1 para Metalia

* **Estado:** Confirmado
* **Fecha:** 2026-10-16
* **Metodología:** `/director-dev` (Humanio CEO + SBD + TDD)
* **Nivel de Riesgo:** `R3` (Crítico / Financiero / Fiscal SAT)

---

## 1. Contexto (Mapeo CEO — Contexto)
Metalia (Querétaro / Corredor Industrial del Bajío) comercializa e instala recubrimientos metálicos, paneles aislados tipo sándwich (Multytecho, Galvatecho, Glamet, Econotecho, Multymuro, Superwall) y lámina de acero acanalada/estructural (R-101, R-72, KR-18, Galvateja, Losacero).

A diferencia del e-commerce minorista tradicional, el giro exige resolver cuatro problemas críticos de ingeniería y finanzas:
1. **Geometría de Obra y Despiece Exacto**: Cálculo trigonométrico de cubiertas por pendiente ($f_p = \sqrt{1 + p^2}$), partición longitudinal de vertientes mayores a $12.00\text{ m}$ con traslapes específicos por perfil ($0.1524\text{ m}$ en Galvatecho/Glamet, $0.200\text{ m}$ en Multytecho), y uso del ancho efectivo real de muro ($1.067\text{ m}$ en Multymuro/Superwall para evitar sobreestimar $6.7\%$ la propuesta).
2. **Explosión Automatizada de Materiales (BOM)**: Selección paramétrica de pijas autotaladrantes ($\text{espesor} + 2.5''$), pijas de costura, clips Cal. 18, tapajuntas exclusivos de Multytecho, rollos de butilo, sellador PU y molduras de remate en tramos de $3.05\text{ m}$ (rendimiento efectivo $2.90\text{ m}$).
3. **Inventario Dimensional en Piso, Cortes y Retazos**: Control por lote físico `[SKU + Espesor + Calibre + Color + Largo en metros]` con restricción de estiba $\le 1.50\text{ m}$, corte sobre hojas maestras (generando retazo comercializable cuando el sobrante es $\ge 2.00\text{ m}$, o facturando la hoja comercial inmediata superior si la merma es $< 2.00\text{ m}$), y vigencia estricta de **72 horas hábiles** con anticipo del **50%**.
4. **Cumplimiento Fiscal Carta Porte 3.1**: Cálculo determinista de `PesoBrutoTotal` en kilogramos ($\sum \text{PesoEnKg}$), clasificación de unidad de flete y generación de payload pre-validado para CFDI de Traslado (flota propia) o Ingreso (fletera tercera).

## 2. Ecosistema (Decisión Tecnológica)
* **Backend y Motor CPQ**: **Python 3.12 + FastAPI + Pydantic v2**, utilizando `Decimal` de precisión exacta para todos los cálculos geométricos, financieros y de tonelaje.
* **Suite de Calidad (TDD)**: **`pytest` + `pytest-cov`**, estructurando pruebas unitarias para cada regla (`RN-01` a `RN-09`) y pruebas de integración sobre los endpoints REST y vistas web.
* **Frontend e Interfaz Interactiva**: **Aplicación Web Full-Stack servida por FastAPI** con plantillas semánticas HTML5, **Tokens CSS nativos** bajo estándar de accesibilidad **WCAG 2.1 AA**, y un **Visualizador Geométrico SVG Dinámico en Tiempo Real** (dibujo proporcional de nave, vertientes, líneas de corte $> 12.00\text{ m}$ y vanos).
* **Adaptadores Externos**: Generador de payload oficial JSON **Complemento Carta Porte 3.1 (SAT)** con identificador `IdCCP` (`CCC...` RFC 4122) y generador de propuesta formal con enlace de WhatsApp y resumen imprimible/PDF.

## 3. Orquestación (Máquina de Estados de la Cotización / Pedido)
1. `BORRADOR`: Cálculo técnico abierto en el cotizador (Modo Directo o Modo Nave).
2. `ENVIADA`: Prospecto registrado; vigencia activa por **72 horas hábiles**.
3. `EXPIRADA`: Superadas las 72 horas hábiles sin pago de anticipo; bloquea cobro histórico y exige recálculo a precios y stock vigentes.
4. `ANTICIPO_50_PAGADO`: Pago del $50\%$ registrado; reserva automática de piezas en `Inventario_Dimensional_Piso`.
5. `EN_CORTE_O_PLANTA`: Ejecución de orden de corte sobre hoja maestra (alta automática de retazo si $\text{sobrante} \ge 2.00\text{ m}$) o programación en planta.
6. `LISTA_EMBARQUE`: Material verificado en patio y `PesoBrutoTotal` conciliado.
7. `CARTA_PORTE_TIMBRADA`: Payload Carta Porte 3.1 validado y timbrado con `IdCCP`.
8. `ENTREGADA`: Pedido liquidado al $100\%$ y entregado en obra o patio Querétaro.
