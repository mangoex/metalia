# Metalia CPQ & Inventario Dimensional en Línea (Querétaro)

Sistema Web Configurador de Productos, Precios y Cotizaciones (**CPQ**), Motor de Explosión de Materiales (**BOM / Take-off**), Control de **Inventario Dimensional en Piso (con Órdenes de Corte y Retazos)** y **Pre-Validador Fiscal de Complemento Carta Porte 3.1 (SAT)** para **Metalia-MS, S.A. de C.V.** en el corredor industrial del Bajío (Querétaro).

Desarrollado bajo metodología **`/director-dev` (Humanio CEO + Specification-Based Development [SBD] + Test-Driven Development [TDD])**.

---

## 1. Arquitectura y Módulos del Sistema

| Módulo | Reglas SBD / Historias | Descripción Técnica |
| :--- | :---: | :--- |
| **1. Catálogo Técnico Paramétrico** | `HU-02` | Gestión de propiedades físicas, geométricas y termodinámicas para **Multytecho, Galvatecho, Glamet, Econotecho, Multymuro, Superwall, R-101, KR-18 y Galvateja**. |
| **2. Cotizador Geométrico CPQ Dual** | `RN-01` a `RN-04`, `HU-01`, `HU-02` | **Modo A (Despiece Directo)** y **Modo B (Asistente Geométrico de Nave Industrial)** con factor trigonométrico $f_p = \sqrt{1+p^2}$, partición longitudinal de vertientes $> 12.00\text{ m}$ con traslapes de norma ($0.1524\text{ m}$ / $0.200\text{ m}$), ancho efectivo exacto de muro ($1.067\text{ m}$) y **Visualizador SVG en Tiempo Real**. |
| **3. Motor de Explosión de Materiales (BOM)** | `RN-06` a `RN-08`, `HU-03` | Selección paramétrica de pijas principales ($\text{espesor} + 2.5''$), pijas de costura, clips Galvatecho Cal. 18, tapajuntas exclusivos de Multytecho, rollos de butilo, sellador PU y molduras de remate de $3.05\text{ m}$ (rendimiento útil $2.90\text{ m}$). |
| **4. Inventario Dimensional en Piso, Cortes y Vigencia** | `RN-05`, `HU-04`, `HU-05`, `HU-06` | Matriz en vivo `[SKU + Largo en m]`, límite de seguridad de estiba $\le 1.50\text{ m}$, órdenes de corte sobre hoja maestra con generación automática de retazos comercializables ($\ge 2.00\text{ m}$), vigencia estricta de **72 horas hábiles** por volatilidad del acero y reserva por **50% de anticipo**. |
| **5. Logística Pesada y Pre-Validador Carta Porte 3.1** | `RN-09`, `HU-07` | Dimensionamiento automático de unidad (Camioneta $3.5\text{ t}$, Rabón/Torton o Plataforma Tráiler $40\text{-}48\text{ ft}$), validación determinista $\text{PesoBrutoTotal} == \sum \text{PesoEnKg}$, identificador `IdCCP` (`CCC...` RFC 4122) y permiso SCT (`TPAF01`). |

---

## 2. Estructura del Proyecto

```text
Metalia/
├── docs/
│   ├── adr/001-arquitectura-cpq-metalia.md
│   └── specs/
│       ├── sbd_domain_rules.md
│       └── gherkin_acceptance.feature
├── app/
│   ├── main.py                         # FastAPI Entrypoint + Portal Web SSR
│   ├── models/domain.py                # 5 Entidades Nucleares y Catálogo Querétaro
│   ├── services/
│   │   ├── geometry_engine.py          # RN-01 a RN-04
│   │   ├── bom_engine.py               # RN-06 a RN-08
│   │   ├── inventory_service.py        # RN-05 (Stock en Piso, Cortes y Retazos)
│   │   ├── pricing_quote_service.py    # Vigencia 72h, Anticipo 50%, Instalación m2
│   │   └── logistics_carta_porte.py    # RN-09 (Fletes y Carta Porte 3.1 SAT)
│   ├── api/routes.py                   # API REST (/api/v1/...)
│   └── web/
│       ├── templates/index.html        # UI Accesible WCAG 2.1 AA
│       └── static/
│           ├── css/tokens.css          # Tokens CSS Nativos
│           └── js/cpq_visualizer.js    # Diagrama SVG Dinámico en Tiempo Real
└── tests/
    ├── unit/                           # Suite TDD Unitaria (RN-01 a RN-09)
    └── integration/                    # Suite TDD Integración E2E (API + UI)
```

---

## 3. Ejecución de Pruebas (TDD) y Servidor Local

```powershell
# 1. Ejecutar suite completa de pruebas y cobertura
uv run pytest --cov=app

# 2. Ejecutar linter estático
uv run ruff check .

# 3. Iniciar servidor web interactivo en http://127.0.0.1:8000
uv run uvicorn app.main:app --reload
```
