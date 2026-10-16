# language: es
Característica: Sistema Web CPQ, Explosión BOM, Inventario Dimensional y Carta Porte 3.1 de Metalia
  Como distribuidora e instaladora de paneles aislados y lámina de acero en Querétaro
  Quiero un sistema CPQ con cuantificación geométrica, explosión de materiales, control de inventario por largos y pre-validador de Carta Porte 3.1
  Para cotizar sin errores técnicos ni pérdidas de margen, controlar los cortes y retazos en patio y cumplir con el SAT en carreteras federales

  Escenario: HU-01 Cuantificación geométrica de nave industrial con partición de vertiente mayor a 12m
    Dado que el usuario ingresa Largo = 40.0 m, Ancho = 25.0 m, techo a 2 aguas con pendiente del 5.0%
    Y selecciona el panel de cubierta "Galvatecho" de 1.5 pulgadas con ancho efectivo de 1.000 m y traslape mínimo de 0.1524 m
    Cuando presiona "Calcular Proyecto"
    Entonces el sistema calcula el factor de pendiente 1.001249 y la vertiente inclinada de 12.52 m
    Y detecta que la vertiente supera los 12.00 m recomendados para plataforma de tráiler
    Y divide cada faldón en 2 tramos longitudinales de 6.33 m incluyendo el traslape transversal de 0.1524 m
    Y arroja 40 hileras por agua y 160 piezas totales de tramo (o 80 hileras totales divididas en 2 tramos)
    Y muestra el área con 6% de desperdicio informativo, el Valor R de 10.00 y el peso total en toneladas

  Escenario: HU-02 Cotización directa por despiece con verificación de stock exacto en piso en Querétaro
    Dado que existen 35 piezas de 6.00 m de "Multymuro" 1.5 pulgadas Arena Cal. 26/26 en el almacén de Querétaro
    Cuando el residente de obra captura una partida directa de 20 piezas de 6.00 m de "Multymuro" 1.5 pulgadas Arena Cal. 26/26
    Entonces el sistema utiliza el ancho efectivo de muro de 1.067 m y calcula exactamente 128.04 m2 facturables
    Y confirma disponibilidad inmediata mostrando el distintivo "Disponible en Piso - Entrega Inmediata"

  Escenario: HU-03 Explosión automática de accesorios (BOM) según espesor y sistema de fijación
    Dado un cálculo de cubierta con panel "Galvatecho" de 2.0 pulgadas de espesor
    Cuando se genera la explosión de materiales (BOM)
    Entonces el sistema selecciona pijas autotaladrantes principales de "1/4 x 4 3/4" aplicando la regla espesor + 2.5 pulgadas
    Y asigna clips de fijación Galvatecho calibre 18
    Y asigna 0 piezas de tapajunta por tratarse de fijación expuesta
    Y calcula caballetes y canalones en tramos comerciales de 3.05 m con rendimiento útil de 2.90 m

  Escenario: HU-04 Inclusión de servicio de instalación llave en mano y flete al código postal de obra
    Dado que el usuario tiene una cotización de nave industrial calculada
    Cuando activa la opción "Incluir Instalación Metalia" e ingresa el Código Postal "76220" en Querétaro
    Entonces el sistema agrega la partida de mano de obra de instalación por m2 de cubierta y muro
    Y dimensiona el tipo de transporte y costo de flete según el peso total en toneladas y el largo máximo de pieza

  Escenario: HU-05 Orden de corte sobre hoja maestra en patio y alta automática de retazos comercializables
    Dado un pedido con anticipo pagado de 5 piezas de 7.50 m de "Galvatecho" 1.5 pulgadas
    Y un lote en piso de 10 hojas maestras de 12.20 m con corte habilitado
    Cuando el jefe de almacén confirma la orden de corte sobre las hojas maestras de 12.20 m
    Entonces el sistema descuenta 5 piezas del lote de 12.20 m quedando 5 disponibles
    Y da de alta automáticamente un nuevo lote de 5 piezas de 4.70 m con la etiqueta es_retazo = true

  Escenario: HU-06 Vigencia estricta de 72 horas hábiles por volatilidad del acero y recálculo
    Dado que una cotización fue emitida hace más de 72 horas hábiles y no tiene anticipo pagado
    Cuando el cliente consulta su folio de cotización o intenta registrar el pago al precio histórico
    Entonces el sistema cambia el estado a "EXPIRADA" y muestra el aviso "Cotización Expirada por Vigencia de Precios del Acero"
    Y permite ejecutar un recálculo instantáneo actualizando los importes al precio base y stock del día

  Escenario: HU-07 Pre-validación determinista y generación de payload para Complemento Carta Porte 3.1
    Dado un pedido listo para embarque con 11165.00 kg en paneles y 180.00 kg en accesorios de fijación y remates
    Cuando el coordinador de logística genera los datos del Complemento Carta Porte 3.1
    Entonces el sistema valida que PesoBrutoTotal sea exactamente 11345.00 kg igual a la suma de PesoEnKg de las mercancías
    Y genera un identificador IdCCP válido bajo el estándar RFC 4122 que inicia con los caracteres "CCC"
    Y verifica el código de permiso SCT "TPAF01" y los códigos postales de origen y destino
