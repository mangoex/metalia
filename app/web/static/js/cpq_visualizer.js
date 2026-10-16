/**
 * Controlador Frontend e Ingeniería Visual SVG en Tiempo Real — Metalia CPQ Querétaro
 * Conecta el Cotizador Dual (Modo Nave y Modo Despiece Directo), el Inventario Dimensional en Piso,
 * el Simulador de Órdenes de Corte / Retazos y el Pre-Validador de Carta Porte 3.1.
 */

let currentActiveFolio = null;

function switchCpqMode(mode) {
  const tabNave = document.getElementById("tab-mode-nave");
  const tabDirect = document.getElementById("tab-mode-direct");
  const panelNave = document.getElementById("panel-mode-nave");
  const panelDirect = document.getElementById("panel-mode-direct");

  if (mode === "nave") {
    tabNave.classList.add("active");
    tabNave.setAttribute("aria-selected", "true");
    tabDirect.classList.remove("active");
    tabDirect.setAttribute("aria-selected", "false");
    panelNave.classList.remove("hidden");
    panelDirect.classList.add("hidden");
  } else {
    tabDirect.classList.add("active");
    tabDirect.setAttribute("aria-selected", "true");
    tabNave.classList.remove("active");
    tabNave.setAttribute("aria-selected", "false");
    panelDirect.classList.remove("hidden");
    panelNave.classList.add("hidden");
  }
}

/**
 * Dibuja en el lienzo SVG la sección transversal y planta de la nave industrial,
 * indicando vertientes, pendiente y líneas de corte cuando L_v > 12.00 m.
 */
function renderNaveSvgDiagram(geo, inp) {
  const svg = document.getElementById("nave-svg-canvas");
  if (!svg) return;

  const largo = parseFloat(inp.largo_nave_m) || 40;
  const ancho = parseFloat(inp.ancho_nave_m) || 25;
  const altoMuro = parseFloat(inp.altura_muro_m) || 6;
  const aguas = parseInt(inp.aguas_techo, 10) || 2;
  const pendiente = parseFloat(inp.pendiente_pct) || 5;
  const tramos = geo.tramos_por_vertiente || 1;

  const wallBaseY = 175;
  const wallTopY = 105;
  const ridgeRise = Math.min(55, Math.max(16, pendiente * 2.8));
  const ridgeY = wallTopY - ridgeRise;

  let roofPath = "";
  let cutMarkers = "";

  if (aguas === 2) {
    roofPath = `M 60 ${wallTopY} L 210 ${ridgeY} L 360 ${wallTopY}`;
    if (tramos > 1) {
      // Marca de traslape transversal en cada faldón (> 12.00 m)
      const midLeftX = 135;
      const midLeftY = (wallTopY + ridgeY) / 2;
      const midRightX = 285;
      const midRightY = (wallTopY + ridgeY) / 2;
      cutMarkers = `
        <circle cx="${midLeftX}" cy="${midLeftY}" r="5" fill="#f97316" />
        <circle cx="${midRightX}" cy="${midRightY}" r="5" fill="#f97316" />
        <line x1="${midLeftX}" y1="${midLeftY - 12}" x2="${midLeftX}" y2="${midLeftY + 12}" stroke="#f97316" stroke-width="2" stroke-dasharray="3,2"/>
        <line x1="${midRightX}" y1="${midRightY - 12}" x2="${midRightX}" y2="${midRightY + 12}" stroke="#f97316" stroke-width="2" stroke-dasharray="3,2"/>
        <text x="210" y="${ridgeY - 12}" text-anchor="middle" fill="#fbbf24" font-size="11" font-weight="bold">
          Partición Longitudinal (${tramos} tramos de ${geo.largo_tramo_cortado_m} m + traslape ${geo.traslape_transversal_m} m)
        </text>
      `;
    }
  } else {
    roofPath = `M 60 ${ridgeY} L 360 ${wallTopY}`;
    if (tramos > 1) {
      const midX = 210;
      const midY = (wallTopY + ridgeY) / 2;
      cutMarkers = `
        <circle cx="${midX}" cy="${midY}" r="5" fill="#f97316" />
        <text x="210" y="${ridgeY - 10}" text-anchor="middle" fill="#fbbf24" font-size="11" font-weight="bold">
          Partición Longitudinal (${tramos} tramos de ${geo.largo_tramo_cortado_m} m)
        </text>
      `;
    }
  }

  // Esquema de hileras en planta a la derecha
  const gridLeft = 420;
  const gridWidth = 220;
  const gridTop = 45;
  const gridHeight = 130;
  const numLines = Math.min(20, Math.max(4, Math.round(geo.hileras_por_agua / 2)));
  let gridLinesSvg = "";
  for (let i = 1; i < numLines; i++) {
    const x = gridLeft + (gridWidth / numLines) * i;
    gridLinesSvg += `<line x1="${x}" y1="${gridTop}" x2="${x}" y2="${gridTop + gridHeight}" stroke="#28354a" stroke-width="1" />`;
  }
  if (aguas === 2) {
    const midGridY = gridTop + gridHeight / 2;
    gridLinesSvg += `<line x1="${gridLeft}" y1="${midGridY}" x2="${gridLeft + gridWidth}" y2="${midGridY}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,3" />`;
  }

  // Franjas de iluminación natural translúcida Acrylit G10 (RN-14)
  let skylightsSvg = "";
  if (geo.hileras_luz_natural > 0) {
    const skylightCols = Math.min(numLines - 1, Math.max(1, Math.round((geo.hileras_luz_natural / geo.hileras_totales_cubierta) * numLines)));
    const step = Math.max(2, Math.floor(numLines / skylightCols));
    for (let c = 1; c < numLines; c += step) {
      const colX = gridLeft + (gridWidth / numLines) * c;
      const colW = gridWidth / numLines;
      skylightsSvg += `<rect x="${colX}" y="${gridTop}" width="${colW}" height="${gridHeight}" fill="#fef08a" opacity="0.45" stroke="#facc15" stroke-width="1" stroke-dasharray="2,2" />`;
    }
  }

  const descCubierta = geo.hileras_luz_natural > 0
    ? `Cubierta: ${geo.piezas_totales_cubierta} pzas (${geo.hileras_opacas} opacas + ${geo.hileras_luz_natural} Acrylit G10)`
    : `Total Cubierta: ${geo.piezas_totales_cubierta} pzas (${geo.area_cubierta_con_desperdicio_m2} m² c/desp.)`;

  svg.innerHTML = `
    <!-- Fondo Técnico -->
    <rect x="0" y="0" width="680" height="220" fill="#080c14" rx="8" />
    <text x="20" y="24" fill="#94a3b8" font-size="11" font-family="monospace">
      ELEVACIÓN FRONTAL (Claro W=${ancho}m | Pendiente=${pendiente}% | f_p=${geo.factor_pendiente})
    </text>
    <text x="420" y="24" fill="#94a3b8" font-size="11" font-family="monospace">
      PLANTA DE DESPIECE (${geo.hileras_por_agua} hileras/agua | L=${largo}m)
    </text>

    <!-- Muros y Firme -->
    <line x1="35" y1="${wallBaseY}" x2="385" y2="${wallBaseY}" stroke="#475569" stroke-width="3" />
    <line x1="60" y1="${wallTopY}" x2="60" y2="${wallBaseY}" stroke="#38bdf8" stroke-width="4" />
    <line x1="360" y1="${wallTopY}" x2="360" y2="${wallBaseY}" stroke="#38bdf8" stroke-width="4" />
    <rect x="180" y="${wallBaseY - 38}" width="60" height="38" fill="#1e293b" stroke="#64748b" stroke-width="1.5" />

    <!-- Cubierta -->
    <path d="${roofPath}" fill="none" stroke="#f97316" stroke-width="5" stroke-linecap="round" />
    ${cutMarkers}

    <!-- Cotas de Elevación -->
    <text x="210" y="198" text-anchor="middle" fill="#cbd5e1" font-size="12" font-family="monospace">
      Ancho Claro: ${ancho} m | Vertiente L_v: ${geo.largo_vertiente_m} m | Altura Muro: ${altoMuro} m
    </text>

    <!-- Planta de Cubierta -->
    <rect x="${gridLeft}" y="${gridTop}" width="${gridWidth}" height="${gridHeight}" fill="#0f172a" stroke="#f97316" stroke-width="2" />
    ${skylightsSvg}
    ${gridLinesSvg}
    <text x="${gridLeft + gridWidth / 2}" y="198" text-anchor="middle" fill="#38bdf8" font-size="11" font-family="monospace">
      ${descCubierta}
    </text>
  `;
}

async function previewNaveCalculation() {
  const luzNatural = parseFloat(document.getElementById("nave-luz-natural")?.value) || 0;
  const payload = {
    largo_nave_m: document.getElementById("nave-largo").value,
    ancho_nave_m: document.getElementById("nave-ancho").value,
    altura_muro_m: document.getElementById("nave-alto-muro").value,
    aguas_techo: parseInt(document.getElementById("nave-aguas").value, 10),
    pendiente_pct: document.getElementById("nave-pendiente").value,
    area_huecos_m2: document.getElementById("nave-huecos").value,
    alcance_obra: document.getElementById("nave-alcance").value,
    sku_cubierta: document.getElementById("nave-sku-cubierta").value,
    sku_muro: document.getElementById("nave-sku-muro").value,
    desperdicio_cubierta_pct: document.getElementById("nave-desperdicio").value,
    porcentaje_luz_natural_pct: luzNatural,
  };

  const resp = await fetch("/api/v1/cpq/preview-nave", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) return;
  const data = await resp.json();
  const geo = data.geometria;
  const bom = data.bom;

  renderNaveSvgDiagram(geo, payload);

  // Actualizar métricas técnicas instantáneas
  document.getElementById("res-lv").textContent = `${geo.largo_vertiente_m} m (${geo.tramos_por_vertiente} tramo/s de ${geo.largo_tramo_cortado_m} m)`;
  document.getElementById("res-piezas-cub").textContent = `${geo.piezas_totales_cubierta} pzas (${geo.hileras_totales_cubierta} hileras)`;
  document.getElementById("res-area-cub").textContent = `${geo.area_cubierta_real_m2} m² (c/desp: ${geo.area_cubierta_con_desperdicio_m2} m²)`;
  document.getElementById("res-piezas-muro").textContent = `${geo.piezas_totales_muro} pzas (Ancho ef. ${geo.ancho_efectivo_muro_m} m)`;
  document.getElementById("res-valor-r").textContent = `R-${geo.valor_r_cubierta}`;
  document.getElementById("res-peso-ton").textContent = `${geo.peso_total_paneles_ton} Ton (${geo.peso_total_paneles_kg} kg)`;

  if (document.getElementById("res-luz-natural")) {
    document.getElementById("res-luz-natural").textContent = `${geo.porcentaje_luz_natural_pct || luzNatural}% (${geo.hileras_luz_natural || 0} hileras)`;
  }
  if (document.getElementById("res-margen-pct")) {
    const margenVal = document.getElementById("nave-margen-utilidad")?.value || 25;
    document.getElementById("res-margen-pct").textContent = `${margenVal}%`;
  }

  // Estimación de flete dinámico
  const tipoEntrega = document.getElementById("cli-entrega")?.value;
  const estadoDest = document.getElementById("cli-estado-destino")?.value;
  const munDest = document.getElementById("cli-municipio-destino")?.value;
  const fleteEl = document.getElementById("res-flete-costo");
  if (fleteEl) {
    if (tipoEntrega === "FLETE_OBRA" && estadoDest && munDest) {
      try {
        const mlCub = (geo.piezas_totales_cubierta || 0) * (parseFloat(geo.largo_tramo_cortado_m) || 0);
        const fleteResp = await fetch("/api/v1/fletes/calculate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            estado: estadoDest,
            municipio: munDest,
            tipo_aplicacion: "TECHO",
            espesor_pulg: "1.5",
            longitud_total_ml: mlCub.toFixed(2),
            peso_total_kg: geo.peso_total_paneles_kg,
          }),
        });
        if (fleteResp.ok) {
          const fData = await fleteResp.json();
          fleteEl.textContent = `$${parseFloat(fData.costo_flete_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
        }
      } catch (err) {
        console.warn("Flete lookup warn:", err);
      }
    } else {
      fleteEl.textContent = "$0.00 MXN (Patio QRO)";
    }
  }

  const slopeAlert = document.getElementById("slope-alert-banner");
  if (geo.alerta_pendiente_minima) {
    slopeAlert.textContent = geo.mensaje_alerta_pendiente;
    slopeAlert.className = "alert-banner badge-danger";
  } else {
    slopeAlert.textContent = geo.mensaje_alerta_pendiente;
    slopeAlert.className = "alert-banner badge-stock";
  }

  // Poblar tabla BOM
  const tbody = document.getElementById("bom-preview-tbody");
  tbody.innerHTML = bom.items
    .map(
      (it) => `
      <tr>
        <td><span class="badge badge-plant">${it.tipo_regla}</span></td>
        <td><strong>${it.descripcion}</strong><br><small class="mono">${it.sku}</small></td>
        <td class="mono">${it.cantidad} ${it.unidad}</td>
        <td class="mono">${it.peso_total_kg} kg</td>
        <td class="mono">$${parseFloat(it.importe_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })}</td>
      </tr>
    `
    )
    .join("");
}

async function generateFormalNaveQuote(event) {
  event.preventDefault();
  const payload = {
    cliente_nombre: document.getElementById("cli-nombre").value,
    cliente_empresa: document.getElementById("cli-empresa").value,
    cliente_whatsapp: document.getElementById("cli-whatsapp").value,
    cliente_email: document.getElementById("cli-email").value,
    largo_nave_m: document.getElementById("nave-largo").value,
    ancho_nave_m: document.getElementById("nave-ancho").value,
    altura_muro_m: document.getElementById("nave-alto-muro").value,
    aguas_techo: parseInt(document.getElementById("nave-aguas").value, 10),
    pendiente_pct: document.getElementById("nave-pendiente").value,
    area_huecos_m2: document.getElementById("nave-huecos").value,
    alcance_obra: document.getElementById("nave-alcance").value,
    sku_cubierta: document.getElementById("nave-sku-cubierta").value,
    sku_muro: document.getElementById("nave-sku-muro").value,
    desperdicio_cubierta_pct: document.getElementById("nave-desperdicio").value,
    porcentaje_luz_natural_pct: parseFloat(document.getElementById("nave-luz-natural")?.value) || 0,
    descuento_planta_pct: (parseFloat(document.getElementById("nave-desc-planta")?.value) || 34) / 100,
    margen_utilidad_pct: (parseFloat(document.getElementById("nave-margen-utilidad")?.value) || 25) / 100,
    es_espuma_fm: document.getElementById("chk-espuma-fm")?.checked || false,
    estado_destino: document.getElementById("cli-estado-destino")?.value || null,
    municipio_destino: document.getElementById("cli-municipio-destino")?.value || null,
    incluir_bom_accesorios: document.getElementById("chk-bom").checked,
    incluir_estructura_polin: document.getElementById("chk-polin").checked,
    incluir_instalacion: document.getElementById("chk-instalacion").checked,
    codigo_postal_obra: document.getElementById("cli-cp").value,
    tipo_entrega: document.getElementById("cli-entrega").value,
  };

  const resp = await fetch("/api/v1/quotes/nave", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) return;
  const quote = await resp.json();
  renderGeneratedQuote(quote);
}

async function evaluateDirectDespieceStock() {
  const sku = document.getElementById("dir-sku").value;
  const pzas = document.getElementById("dir-piezas").value;
  const largo = document.getElementById("dir-largo").value;

  const url = `/api/v1/cpq/evaluate-stock?sku=${encodeURIComponent(sku)}&cantidad_piezas=${encodeURIComponent(pzas)}&largo_requerido_m=${encodeURIComponent(largo)}`;
  const resp = await fetch(url, { method: "POST" });
  if (!resp.ok) return;
  const alloc = await resp.json();

  const box = document.getElementById("direct-eval-result");
  let badgeClass = "badge-stock";
  if (alloc.origen_suministro === "CORTE_HOJA_MAESTRA") badgeClass = "badge-cut";
  if (alloc.origen_suministro === "FABRICACION_PLANTA") badgeClass = "badge-plant";

  box.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
      <span class="badge ${badgeClass}">${alloc.distintivo_disponibilidad}</span>
      <span class="mono">Ancho Efectivo: <strong>${alloc.ancho_efectivo_m} m</strong> | Área Facturable: <strong>${alloc.area_m2_facturada} m²</strong></span>
      <span class="mono">Peso: <strong>${alloc.peso_total_kg} kg</strong> | Subtotal: <strong>$${parseFloat(alloc.importe_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN</strong></span>
    </div>
  `;
}

async function generateDirectQuote(event) {
  event.preventDefault();
  const payload = {
    cliente_nombre: document.getElementById("cli-nombre").value,
    cliente_empresa: document.getElementById("cli-empresa").value,
    cliente_whatsapp: document.getElementById("cli-whatsapp").value,
    cliente_email: document.getElementById("cli-email").value,
    codigo_postal_obra: document.getElementById("cli-cp").value,
    tipo_entrega: document.getElementById("cli-entrega").value,
    incluir_instalacion: document.getElementById("dir-chk-instalacion").checked,
    lineas: [
      {
        sku: document.getElementById("dir-sku").value,
        cantidad_piezas: parseInt(document.getElementById("dir-piezas").value, 10),
        largo_pieza_m: document.getElementById("dir-largo").value,
      },
    ],
  };

  const resp = await fetch("/api/v1/quotes/direct", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) return;
  const quote = await resp.json();
  renderGeneratedQuote(quote);
}

function renderGeneratedQuote(quote) {
  currentActiveFolio = quote.folio;
  const section = document.getElementById("active-quote-section");
  section.classList.remove("hidden");

  document.getElementById("q-folio").textContent = quote.folio;
  document.getElementById("q-estado").textContent = quote.estado;
  document.getElementById("q-vigencia").textContent = quote.mensaje_vigencia;
  document.getElementById("q-transporte").textContent = quote.unidad_transporte_sugerida;
  document.getElementById("q-peso-kg").textContent = `${quote.peso_bruto_total_kg} kg (${quote.peso_bruto_total_ton} Ton)`;
  document.getElementById("q-subtotal").textContent = `$${parseFloat(quote.subtotal_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  document.getElementById("q-total").textContent = `$${parseFloat(quote.total_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  document.getElementById("q-anticipo").textContent = `$${parseFloat(quote.anticipo_50_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  document.getElementById("q-whatsapp-link").href = quote.whatsapp_share_url;

  const tbody = document.getElementById("q-partidas-tbody");
  tbody.innerHTML = quote.partidas
    .map(
      (p) => `
      <tr>
        <td><span class="badge badge-plant">${p.subsistema}</span></td>
        <td><strong>${p.descripcion}</strong><br><small>${p.distintivo_disponibilidad}</small></td>
        <td class="mono">${p.cantidad_piezas} ${p.unidad}</td>
        <td class="mono">${p.peso_partida_kg} kg</td>
        <td class="mono">$${parseFloat(p.importe_mxn).toLocaleString("es-MX", { minimumFractionDigits: 2 })}</td>
      </tr>
    `
    )
    .join("");

  // Desglose financiero comercial en cascada (RN-11, RN-12)
  if (document.getElementById("q-costo-neto")) {
    document.getElementById("q-costo-neto").textContent = `$${parseFloat(quote.costo_total_material_mxn || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  }
  if (document.getElementById("q-venta-sin-flete")) {
    document.getElementById("q-venta-sin-flete").textContent = `$${parseFloat(quote.importe_venta_sin_flete_mxn || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  }
  if (document.getElementById("q-utilidad-bruta")) {
    document.getElementById("q-utilidad-bruta").textContent = `$${parseFloat(quote.utilidad_bruta_mxn || 0).toLocaleString("es-MX", { minimumFractionDigits: 2 })} MXN`;
  }
  if (document.getElementById("q-margen-bruto-pct")) {
    document.getElementById("q-margen-bruto-pct").textContent = `${quote.margen_bruto_pct || 0}%`;
  }
  const alertaBanner = document.getElementById("q-alerta-margen-banner");
  if (alertaBanner) {
    if (quote.alerta_margen_bajo) {
      alertaBanner.classList.remove("hidden");
    } else {
      alertaBanner.classList.add("hidden");
    }
  }

  section.scrollIntoView({ behavior: "smooth" });
  refreshCatalogAndInventory();
}

async function payAdvance50ForActiveQuote() {
  if (!currentActiveFolio) return;
  const resp = await fetch(`/api/v1/quotes/${currentActiveFolio}/advance-payment`, {
    method: "POST",
  });
  if (!resp.ok) return;
  const updated = await resp.json();
  renderGeneratedQuote(updated);
}

async function generateCartaPorteForActiveQuote() {
  if (!currentActiveFolio) return;
  const resp = await fetch(`/api/v1/quotes/${currentActiveFolio}/carta-porte`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      modalidad_transporte: document.getElementById("cp-modalidad").value,
      permiso_sct: "TPAF01",
      numero_permiso_sct: "SCT-QRO-2026-8842",
      config_vehicular: "T3S2",
      placa_vm: document.getElementById("cp-placa").value,
      anio_modelo_vm: 2025,
      subtipo_remolque: "CTR021",
      placa_remolque: "99RM1A",
      operador_nombre: document.getElementById("cp-operador").value,
      operador_rfc: "TOMA820512QRO",
      operador_licencia: "FED776655",
    }),
  });
  if (!resp.ok) return;
  const cpPayload = await resp.json();
  const viewer = document.getElementById("carta-porte-json-output");
  viewer.textContent = JSON.stringify(cpPayload, null, 2);
  document.getElementById("q-estado").textContent = "CARTA_PORTE_TIMBRADA";
}

async function runWarehouseCutOrder(event) {
  event.preventDefault();
  const payload = {
    id_lote_origen: document.getElementById("cut-lote-id").value,
    cantidad_piezas: parseInt(document.getElementById("cut-cantidad").value, 10),
    largo_corte_m: document.getElementById("cut-largo").value,
  };
  const resp = await fetch("/api/v1/inventory/cut-orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const msgEl = document.getElementById("cut-order-feedback");
  if (!resp.ok) {
    const err = await resp.json();
    msgEl.textContent = `Error: ${err.detail}`;
    msgEl.className = "alert-banner badge-danger";
    return;
  }
  const res = await resp.json();
  if (res.genero_retazo) {
    msgEl.textContent = `Orden ${res.id_orden_corte} ejecutada: Se descontaron ${res.cantidad_cortada} hojas madre y se dio de alta automáticamente el lote de retazo ${res.lote_retazo.id_lote} de ${res.sobrante_m} m (es_retazo = true).`;
    msgEl.className = "alert-banner badge-stock";
  } else {
    msgEl.textContent = `Orden ${res.id_orden_corte} ejecutada: Merma de ${res.sobrante_m} m (< 2.00 m invendible). No se generó retazo.`;
    msgEl.className = "alert-banner badge-cut";
  }
  await refreshCatalogAndInventory();
}

async function refreshCatalogAndInventory() {
  const resp = await fetch("/api/v1/catalog");
  if (!resp.ok) return;
  const data = await resp.json();
  const tbody = document.getElementById("inventory-live-tbody");
  if (!tbody) return;

  tbody.innerHTML = data.inventario_piso
    .map(
      (lot) => `
      <tr>
        <td class="mono">${lot.id_lote}</td>
        <td><strong>${lot.sku}</strong></td>
        <td class="mono"><strong>${lot.largo_pieza_m} m</strong></td>
        <td class="mono">${lot.cantidad_piezas_disponibles} pzas</td>
        <td class="mono">${lot.cantidad_piezas_reservadas} pzas</td>
        <td>
          ${
            lot.es_retazo
              ? '<span class="badge badge-cut">Retazo Comercializable</span>'
              : lot.admite_corte
              ? '<span class="badge badge-stock">Hoja Maestra (Admite Corte)</span>'
              : '<span class="badge badge-plant">Medida Estándar Piso</span>'
          }
        </td>
        <td class="mono">${lot.ubicacion_patio} (Estiba ${lot.altura_estiba_m} m ≤ 1.50 m)</td>
      </tr>
    `
    )
    .join("");
}

async function onFreightStateChanged() {
  const estado = document.getElementById("cli-estado-destino")?.value;
  const munSelect = document.getElementById("cli-municipio-destino");
  if (!estado || !munSelect) return;
  try {
    const resp = await fetch(`/api/v1/fletes/destinos?estado=${encodeURIComponent(estado)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.destinos && data.destinos.length > 0) {
      munSelect.innerHTML = data.destinos.map((d) => `<option value="${d}">${d}</option>`).join("");
      previewNaveCalculation();
    }
  } catch (err) {
    console.warn("Error cargando destinos de flete:", err);
  }
}

async function initFreightDropdowns() {
  const estSelect = document.getElementById("cli-estado-destino");
  if (!estSelect) return;
  try {
    const resp = await fetch("/api/v1/fletes/estados");
    if (!resp.ok) return;
    const data = await resp.json();
    if (data.estados && data.estados.length > 0) {
      estSelect.innerHTML = data.estados
        .map((e) => `<option value="${e}" ${e === "Querétaro" ? "selected" : ""}>${e}</option>`)
        .join("");
      await onFreightStateChanged();
    }
  } catch (err) {
    console.warn("Error inicializando fletes:", err);
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  await initFreightDropdowns();
  previewNaveCalculation();
  evaluateDirectDespieceStock();
});
