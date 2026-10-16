# Especificación SBD (Specification-Based Development) — Reglas de Dominio Metalia CPQ

## 1. Catálogo Maestro de Familias y Parámetros Técnicos

| Código Familia | Modelo Comercial | Mecanismo Fijación | Ancho Efectivo ($W_{\text{ef}}$) | Espesores Disponibles | Calibres | Largo Mín / Máx Plataforma / Máx Planta | Traslape Transversal Mín ($T_{\min}$) | Desperdicio Default ($d$) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `PANEL_TECHO` | `Multytecho` | `OCULTA_TAPAJUNTA` | $1.000\text{ m}$ | $1.0''\text{ a }6.0''$ | $26/26, 26/28, 28/28$ | $2.50\text{ m} / 12.00\text{ m} / 14.63\text{ m}$ | $0.200\text{ m}$ ($8''$) | $6\%$ ($0.06$) |
| `PANEL_TECHO` | `Galvatecho` / `Glamet` | `EXPUESTA_TRASLAPE` | $1.000\text{ m}$ | $1.0''\text{ a }4.0''$ | $26/26, 26/28$ | $2.00\text{ m} / 12.00\text{ m} / 14.63\text{ m}$ | $0.1524\text{ m}$ ($6''$) | $6\%$ ($0.06$) |
| `PANEL_TECHO` | `Econotecho` / `Glamet LV` | `EXPUESTA_TRASLAPE` | $1.000\text{ m}$ | $1.0'', 1.5'', 2.0''$ | $26, 28$ (1 cara acero + Kraft/Vinil) | $2.50\text{ m} / 12.00\text{ m} / 12.00\text{ m}$ | $0.1524\text{ m}$ ($6''$) | $6\%$ ($0.06$) |
| `PANEL_MURO` | `Multymuro` / `Superwall` | `OCULTA_MURO` | $1.067\text{ m}$ | $1.5''\text{ a }6.0''$ | $26/26$ | $2.00\text{ m} / 12.00\text{ m} / 12.00\text{ m}$ | $0.000\text{ m}$ | $6\%$ ($0.06$) |
| `LAMINA_ACANALADA` | `R-101` / `R-72` | `EXPUESTA_TRASLAPE` | $1.016\text{ m}$ (R-101) | Acero simple | $22, 24, 26, 28, 30, 32$ | $2.00\text{ m} / 12.00\text{ m} / 12.00\text{ m}$ | $0.200\text{ m}$ | $10\%$ ($0.10$) |
| `LAMINA_KR18` | `KR-18` / `KR-24` | `ENGARGOLADA` | $0.914\text{ m}$ | Acero simple / MBI | $22, 24, 26$ | $2.00\text{ m} / 12.00\text{ m} / 60.00\text{ m}$ (rolado en sitio) | $0.000\text{ m}$ | $10\%$ ($0.10$) |
| `LAMINA_TEJA` | `Galvateja` | `EXPUESTA_TRASLAPE` | $0.900\text{ m}$ | Acero troquelado | $26, 28$ | $2.00\text{ m} / 12.00\text{ m} / 12.00\text{ m}$ | $0.150\text{ m}$ | $10\%$ ($0.10$) |

---

## 2. Contratos de Reglas de Negocio (`RN-01` a `RN-09`)

### `RN-01` — Factor de Corrección por Pendiente ($f_p$)
* **Entrada**: `pendiente_pct` ($\ge 0$), `pendiente_minima_pct` (por defecto $5.0\%$).
* **Fórmula**:
  $$p = \frac{\text{pendiente\_pct}}{100}, \quad f_p = \sqrt{1 + p^2}$$
* **Salida**: `factor_pendiente` (`Decimal` redondeado a 6 decimales), `alerta_pendiente_minima` (`bool` = `True` si `pendiente_pct < pendiente_minima_pct`), `mensaje_alerta` (`str`).

### `RN-02` — Longitud de Vertiente ($L_v$) y Partición Longitudinal por Transporte ($> 12.00\text{ m}$)
* **Entrada**: `ancho_nave_m` ($W_{\text{nave}}$), `aguas_techo` ($1$ o $2$), `factor_pendiente` ($f_p$), `largo_max_plataforma_m` ($12.00\text{ m}$), `traslape_transversal_min_m` ($T_{\min}$), `rolado_en_sitio` (`bool`, opcional para KR-18).
* **Fórmula**:
  1. $W_{\text{vertiente}} = W_{\text{nave}}$ si `aguas_techo == 1`, o $\frac{W_{\text{nave}}}{2}$ si `aguas_techo == 2`.
  2. $L_v = W_{\text{vertiente}} \times f_p$.
  3. Si $L_v \le 12.00\text{ m}$ (o `rolado_en_sitio == True`):
     * $k = 1$, $L_{\text{tramo}} = \operatorname{round}(L_v, 2)$, `requiere_traslape_transversal = False`.
  4. Si $L_v > 12.00\text{ m}$ y `rolado_en_sitio == False`:
     * $k = \left\lceil \frac{L_v}{12.00} \right\rceil$ tramos por hilera.
     * $L_{\text{tramo}} = \operatorname{round}\left(\frac{L_v + (k - 1) \times T_{\min}}{k}, 2\right)$, `requiere_traslape_transversal = True`.

### `RN-03` — Conteo de Piezas y Superficie de Cubierta ($N_{\text{cub}}$)
* **Entrada**: `largo_nave_m` ($L_{\text{nave}}$), `ancho_nave_m` ($W_{\text{nave}}$), `aguas_techo` ($N_{\text{aguas}}$), `tramos_por_vertiente` ($k$), `largo_tramo_m` ($L_{\text{tramo}}$), `ancho_efectivo_m` ($W_{\text{ef}}$), `factor_pendiente` ($f_p$), `desperdicio_pct` ($d$).
* **Fórmula**:
  * $N_{\text{hileras}} = \left\lceil \frac{L_{\text{nave}}}{W_{\text{ef}}} \right\rceil$
  * $N_{\text{cub}} = N_{\text{aguas}} \times k \times N_{\text{hileras}}$
  * $A_{\text{cub\_real}} = L_{\text{nave}} \times W_{\text{nave}} \times f_p$
  * $A_{\text{cub\_con\_desperdicio}} = A_{\text{cub\_real}} \times (1 + d)$
  * $A_{\text{cub\_facturada}} = N_{\text{cub}} \times L_{\text{tramo}} \times W_{\text{ef}}$

### `RN-04` — Superficie y Piezas de Muro Perimetral ($N_{\text{muro}}$)
* **Entrada**: `largo_nave_m` ($L_{\text{nave}}$), `ancho_nave_m` ($W_{\text{nave}}$), `altura_muro_m` ($H_{\text{muro}}$), `area_huecos_m2` ($A_{\text{huecos}}$), `ancho_efectivo_muro_m` ($1.067\text{ m}$ para Multymuro/Superwall), `desperdicio_pct` ($d = 0.06$).
* **Fórmula**:
  * Perímetro $P = 2 \times (L_{\text{nave}} + W_{\text{nave}})$.
  * Área bruta $A_{\text{muro\_bruta}} = P \times H_{\text{muro}}$.
  * Área neta $A_{\text{muro\_neta}} = \max(0,\ A_{\text{muro\_bruta}} - A_{\text{huecos}})$.
  * Área con desperdicio $A_{\text{muro\_con\_desperdicio}} = A_{\text{muro\_neta}} \times (1 + d)$.
  * Conteo de piezas verticales de largo $H_{\text{muro}}$:
    $$N_{\text{muro}} = \left\lceil \frac{A_{\text{muro\_neta}}}{H_{\text{muro}} \times W_{\text{ef\_muro}}} \right\rceil$$

### `RN-05` — Asignación de Inventario Dimensional en Piso, Cortes y Retazos
* **Reglas de Asignación**:
  1. **Stock Exacto en Piso (`STOCK_EXACTO_PISO`)**: Si existe en `Inventario_Dimensional_Piso` un lote de la variante con `largo_pieza_m == L_requerido` y `cantidad_piezas_disponibles >= cantidad_requerida`, se asigna directamente con `largo_facturado_m = L_requerido` y distintivo `"Disponible en Piso - Entrega Inmediata"`.
  2. **Corte desde Hoja Comercial o Hoja Maestra (`CORTE_HOJA_MAESTRA`)**: Si no hay match exacto pero la variante es estándar y existe lote con `largo_pieza_m > L_requerido`, `admite_corte == True` y `cantidad_piezas_disponibles >= cantidad_requerida` (ordenado por `largo_pieza_m` ascendente):
     * $\text{sobrante\_m} = \text{largo\_hoja\_m} - L_{\text{requerido}}$.
     * Si $\text{sobrante\_m} < 2.00\text{ m}$ (merma invendible): se cobra la hoja completa (`largo_facturado_m = largo_hoja_m`) y al confirmar el corte no se ingresa retazo.
     * Si $\text{sobrante\_m} \ge 2.00\text{ m}$ (retazo comercializable, ej. hoja maestra de $12.20\text{ m} - 7.50\text{ m} = 4.70\text{ m}$): al ejecutar la orden de corte se descuentan $N$ piezas del lote de $12.20\text{ m}$ y se crean automáticamente $N$ piezas de $4.70\text{ m}$ con `es_retazo = True`.
  3. **Fabricación Especial en Planta (`FABRICACION_PLANTA`)**: Si la variante tiene `es_estandar_en_piso == False` (ej. espesores $\ge 2.5''$, espuma Clase 1 FM, acabados Duraplus/Plastisol) o no hay stock suficiente en piso/hoja maestra, se marca como `"Fabricación Especial Bajo Pedido (Sujeto a tiempos de planta)"`.
  4. **Seguridad Industrial en Patio**: Ningún lote puede registrarse con `altura_estiba_m > 1.50`.

### `RN-06` — Selección y Cuantificación de Tornillería y Clips
* **Pija Principal Estructural ($1/4''$ Hexagonal con arandela EPDM)**:
  * Longitud requerida en pulgadas $= \text{espesor\_pulg} + 2.5''$.
  * Mapeo de catálogo comercial:
    * Espesor $1.0'' \to$ Pija $1/4'' \times 3\ 1/2''$ (`PIJA-HEX-14-350`)
    * Espesor $1.5'' \to$ Pija $1/4'' \times 4''$ (`PIJA-HEX-14-400`)
    * Espesor $2.0'' \to$ Pija $1/4'' \times 4\ 3/4''$ (`PIJA-HEX-14-475`)
    * Espesor $2.5'' \to$ Pija $1/4'' \times 5''$ (`PIJA-HEX-14-500`)
    * Espesor $\ge 3.0'' \to$ Pija $1/4'' \times (\text{espesor} + 2.5'')$ (`PIJA-HEX-14-ESP`)
    * Lámina simple (sin núcleo) $\to$ Pija $1/4'' \times 1''$ (`PIJA-HEX-14-100`)
  * Cantidad de pijas principales $= \left\lceil A_{\text{cub\_real}} \times 8 \right\rceil$ (o proporcional al área de cubierta/muro).
* **Pija de Costura (Cosido de traslapes y molduras $1/4'' \times 7/8''$ o $1/4'' \times 1/2''$)**:
  * Cantidad $= \left\lceil A_{\text{cub\_real}} \times 4 \right\rceil$.
* **Clips de Fijación**:
  * Si `modelo` es `Galvatecho`, `Glamet`, `Econotecho` o `Glamet LV` (`EXPUESTA_TRASLAPE` en panel aislado): Cantidad de Clips Galvatecho Cal. 18 ($47 \times 38\text{ mm}$) $= \left\lceil A_{\text{cub\_real}} \times 2.5 \right\rceil$ (1 clip por pija de apoyo en cresta).
  * Si `mecanismo_fijacion == OCULTA_TAPAJUNTA` (`Multytecho`): Clips ocultos de fijación $= \left\lceil A_{\text{cub\_real}} \times 2.5 \right\rceil$.

### `RN-07` — Tapajuntas Longitudinales (Exclusivo Multytecho)
* Si `mecanismo_fijacion == OCULTA_TAPAJUNTA`:
  $$\text{Piezas de Tapajunta} = N_{\text{aguas}} \times k \times \max(0,\ N_{\text{hileras}} - 1)$$
  con largo unitario igual a $L_{\text{tramo}}$.
* Para cualquier otro mecanismo de fijación (`EXPUESTA_TRASLAPE`, `OCULTA_MURO`, `ENGARGOLADA`), $\text{Piezas de Tapajunta} = 0$.

### `RN-08` — Molduras de Remate, Canalones, Bajadas y Selladores
* Longitud comercial de moldura $= 3.05\text{ m}$; traslape $= 0.15\text{ m} \implies$ rendimiento útil $= 2.90\text{ m}$.
* **Caballete central ($3.05\text{ m}$)**: Si $N_{\text{aguas}} == 2 \implies \left\lceil \frac{L_{\text{nave}}}{2.90} \right\rceil$ piezas (y $2$ tapas de caballete por hilera o lote). Si $N_{\text{aguas}} == 1 \implies 0$ caballetes centrales (se usa remate superior contra muro/cumbrera).
* **Canalón pluvial ($3.05\text{ m}$)**: $\left\lceil \frac{N_{\text{aguas}} \times L_{\text{nave}}}{2.90} \right\rceil$ piezas.
* **Bajadas pluviales**: $\left\lceil \frac{N_{\text{aguas}} \times L_{\text{nave}}}{12.00} \right\rceil$ piezas.
* **Remates laterales / Botaguas ($3.05\text{ m}$)**: $\left\lceil \frac{2 \times N_{\text{aguas}} \times L_v}{2.90} \right\rceil$ piezas.
* **Subsistema de Muros (cuando `alcance_obra` incluye muros)**:
  * Canal U de base ($3.05\text{ m}$): $\left\lceil \frac{P}{2.90} \right\rceil$ piezas.
  * Esquineros interiores y exteriores ($3.05\text{ m}$): $2 \times \left\lceil \frac{4 \times H_{\text{muro}}}{2.90} \right\rceil$ piezas.
* **Cinta de Butilo (rollos de $10\text{ m}$)**: $\left\lceil \frac{\text{Metros lineales de traslape y caballete}}{10.0} \right\rceil$ rollos (mínimo $1$ en toda cubierta).

### `RN-09` — Peso Logístico Determinista y Pre-Validador Carta Porte 3.1
* Cada partida calcula `peso_partida_kg` con precisión `Decimal(0.01)`:
  * Para paneles y láminas: $\text{Área Facturada m}^2 \times \text{peso\_kg\_m2}$.
  * Para accesorios/molduras/polines: $\text{Cantidad} \times \text{peso\_unitario\_kg}$.
* `PesoBrutoTotal` $= \sum \text{peso\_partida\_kg}$.
* El generador de **Complemento Carta Porte 3.1**:
  1. Valida que `PesoBrutoTotal` sea estrictamente igual a la suma de `PesoEnKg` de todas las mercancías físicas (excluyendo servicios intangibles como instalación y flete).
  2. Genera `IdCCP` bajo formato RFC 4122 donde los primeros 3 caracteres son `CCC` (`CCC` + 5 dígitos hex + `-` + ...).
  3. Valida código postal de origen (Querétaro, ej. `76000` / `76220`), código postal de destino (5 dígitos numéricos) y permiso SCT (`TPAF01`).
  4. Distingue `CFDI_TRASLADO` (flota propia Metalia, subtotal y total $\$0.00\text{ MXN}$) de `CFDI_INGRESO` (transportista tercero con cobro de flete + IVA).

### `RN-10` — Motor Dinámico de Fletes Nacionales (1,239 Municipios)
* **Entrada**: `estado_destino` (`str`), `municipio_destino` (`str`), `tipo_aplicacion` (`TECHO` o `MURO`), `espesor_pulg` (`str`, ej. `"1.5\""`), `longitud_total_ml` (`Decimal`), `peso_total_kg` (`Decimal`).
* **Regla de Búsqueda y Cálculo**:
  1. Se consulta el registro de destino en la matriz nacional oficial (`Fletes 2023`).
  2. Si el producto es panel aislado con espesor:
     * Para techo: se obtiene la tarifa unitaria en $\text{\$/ml}$ según columna de espesor ($1'', 1.5'', 2'', 2.5'', 3'', 4'', 5'', 6''$).
     * Para muro: se obtiene la tarifa unitaria en $\text{\$/ml}$ según columna de espesor de muro ($1.5'', 2'', 2.5'', 3'', 4'', 5'', 6''$).
     * Flete panel $= \operatorname{round}(\text{longitud\_total\_ml} \times \text{tarifa\_ml}, 2)$.
  3. Si el producto es acanalado simple, losacero o accesorio (sin tarifa por ml de panel):
     * Flete por tonelada $= \operatorname{round}\left(\frac{\text{peso\_total\_kg}}{1000} \times \text{costo\_ton\_mxn}, 2\right)$.
  4. Si no se selecciona municipio específico o es entrega en patio Querétaro (`LAB_PATIO_QRO`), el flete es $\$0.00\text{ MXN}$.

### `RN-11` — Estructura Comercial en Cascada y Opción Técnica Espuma FM Clase I
* **Entrada**: `precio_lista_base_m2`, `descuento_planta_pct` ($0 \le d \le 0.50$, default $0.34$ en panel, $0.28$ en acanalado), `indirecto_pct` ($0 \le i \le 0.20$, default $0.00$), `margen_utilidad_pct` ($0.10 \le m \le 0.60$, default $0.25$), `es_espuma_fm` (`bool`, default `False`).
* **Fórmula de Cascada Comercial**:
  1. Factor Espuma FM:
     $$\text{Precio Lista Ajustado} = \begin{cases} \text{precio\_lista\_base\_m2} \times 1.07 & \text{si } \text{es\_espuma\_fm} = \text{True} \\ \text{precio\_lista\_base\_m2} & \text{si } \text{es\_espuma\_fm} = \text{False} \end{cases}$$
  2. Costo Neto de Compra a Planta:
     $$\text{Costo Neto Planta} = \text{Precio Lista Ajustado} \times (1 - \text{descuento\_planta\_pct})$$
  3. Costo con Indirecto Operativo:
     $$\text{Costo con Indirecto} = \text{Costo Neto Planta} \times (1 + \text{indirecto\_pct})$$
  4. Precio de Venta Base (sin flete):
     $$\text{Precio Venta sin Flete} = \text{Costo con Indirecto} \times (1 + \text{margen\_utilidad\_pct})$$
  5. Precio Unitario Final con Flete:
     $$\text{P.U. Final Venta} = \text{Precio Venta sin Flete} + \text{Flete Unitario por m}^2$$

### `RN-12` — Trazabilidad Financiera y Control de Margen Institucional
* Toda cotización calcula y expone métricas financieras de gerencia:
  * `costo_total_material_mxn` $= \sum (\text{Costo con Indirecto}_i \times \text{Cantidad}_i)$
  * `importe_venta_material_sin_flete_mxn` $= \sum (\text{Precio Venta sin Flete}_i \times \text{Cantidad}_i)$
  * `utilidad_bruta_mxn` $= \text{importe\_venta\_material\_sin\_flete\_mxn} - \text{costo\_total\_material\_mxn}$
  * `margen_bruto_pct` $= \frac{\text{utilidad\_bruta\_mxn}}{\text{importe\_venta\_material\_sin\_flete\_mxn}} \times 100$
* **Alerta de Margen Mínimo**: Si $\text{margen\_bruto\_pct} < 15.0\%$, se activa una bandera de aviso `ALERTA_MARGEN_BAJO` requiriendo autorización de gerencia comercial.

### `RN-13` — Catálogo Técnico de Acanalados Simples y Losacero
* **Ternium TR-101**: Ancho efectivo $W_{\text{ef}} = 1.008\text{ m}$ ($100.8\text{ cm}$), calibres $20, 22, 24, 26, 28, 30$, peralte $2.5\text{ cm}$, fijación expuesta en cresta.
* **Ternium TR-72**: Ancho efectivo $W_{\text{ef}} = 0.720\text{ m}$ ($72.0\text{ cm}$), calibres $22, 24, 26, 28, 30, 32$, peralte $2.5\text{ cm}$.
* **Ternium Losacero 25 / 15**: Ancho efectivo $W_{\text{ef}} = 0.9144\text{ m}$ ($91.44\text{ cm}$), calibres $18, 20, 22, 24$, peralte $6.35\text{ cm}$ (Losacero 25) y $3.81\text{ cm}$ (Losacero 15).
* A diferencia del panel sándwich, los acanalados no llevan clips ni tapajuntas; usan pijas principales de $1/4'' \times 1''$ y pijas de costura $1/4'' \times 7/8''$.

### `RN-14` — Franjas de Iluminación Natural con Translúcidos Stabilit
* Modelos: `Acrylit G10` (100% Acrílico con protección GelCoat) y `Poliacryl G5` (Poliéster reforzado con fibra de vidrio).
* Perfil geométrico troquelado idéntico al panel o acanalado de cubierta (ej. perfil compatible con TR-101 o Multytecho).
* Entrada: `porcentaje_luz_natural_pct` ($0\%$ a $25\%$, default $0\%$).
* Si `porcentaje_luz_natural_pct > 0`:
  * $N_{\text{franjas}} = \max\left(1,\ \operatorname{round}\left(N_{\text{hileras}} \times \frac{\text{porcentaje\_luz\_natural\_pct}}{100}\right)\right)$.
  * Se sustituyen $N_{\text{franjas}}$ hileras de panel opaco por hileras de lámina translúcida.
  * El BOM agrega sellador de poliuretano y cinta de butilo adicional para garantizar estanqueidad en los traslapes de las franjas translúcidas.

### `RN-15` — Molduras de Hojalatería con Códigos WizERP y Desarrollo
* Cada moldura define su desarrollo desplegado en centímetros ($D$) y largo estándar de $3.05\text{ m}$.
* A partir de bobina o lámina lisa master de $1.22\text{ m}$ ($122\text{ cm}$):
  $$\text{Tiras Útiles por Lámina} = \left\lfloor \frac{122.0}{D} \right\rfloor$$
* El costo unitario de moldura se compone de:
  $$\text{Costo Lámina por Tira} = \frac{\text{Costo Lámina Master}}{\text{Tiras Útiles por Lámina}}$$
  $$\text{Costo Base Habilitado} = \text{Costo Lámina por Tira} + \text{Costo Maquila Doblez}$$
* Códigos WizERP integrados:
  * `CIIPFC2215305152`: Canal Inferior Interior 1.5" ($D=15.1\text{ cm}$, 8 tiras, maquila \$55).
  * `CIIPFC2220305174`: Canal Inferior Interior 2" ($D=17.4\text{ cm}$, 7 tiras, maquila \$55).
  * `TGPFC24305244`: Tapagotero estándar Cal. 24 ($D=24.4\text{ cm}$, 5 tiras, maquila \$70).
  * `CABALLETE_LISO`: Caballete cumbrera $3.05\text{ m}$ ($D=40.0\text{ cm}$, 3 tiras, maquila \$80).
