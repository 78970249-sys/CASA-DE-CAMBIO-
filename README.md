# CasaDeCambio — Servicio Profesional de Divisas

Proyecto **B** del trabajo colaborativo por ramas (Feature Branch Workflow).
Aplicación de consola **(con GUI demo en tkinter)** donde el operador de
una casa de cambio cotiza divisas contra el dólar estadounidense (USD),
registra clientes, ejecuta compras y ventas, imprime tickets, lleva el
historial y realiza el cierre de caja del día (arqueo).

Desarrollado con **arquitectura en capas adaptada a POO** y
**Co-pilotaje por Células de Desarrollo (Human-AI Co-creation)**: los
integrantes actúan como *operadores y auditores* del código generado con
agentes de IA.

---

## 1. Requerimientos del proyecto

- Python **3.10+** (usa `str | None`, `set[int, ...]`, `dataclasses`).
- Ninguna dependencia externa: solo la biblioteca estándar (incluso la GUI).
- Pruebas con `unittest` (biblioteca estándar).

## 2. Ejecutar (validación humana local)

Desde la carpeta raíz del proyecto:

```bash
# Ejecutar la aplicación
python src/main.py           # interfaz gráfica (tkinter)  -> en Windows: py src/main.py
python src/main.py cli       # interfaz de consola (la de la asignatura)

# Ejecutar las pruebas unitarias
python -m unittest discover -s tests -v
```

> La **GUI (tkinter, sin dependencias externas)** es la presentación del
> Demo Day: cinco pestañas (Operar, Tasas, Clientes, Historial y Caja)
> sobre la misma fachada `AppService` que usa la **CLI** (`cli`), con
> cero cambios en dominio.

### Recorrido rápido de la CLI

```
[1] Ver cotizaciones                     -> pizarra de divisas (C / V en US$)
[2] Operación de compra / venta          -> ejecuta operación + ticket
[3] Actualizar tasas o monedas           -> editar C/V, agregar, eliminar
[4] Clientes (listar, registrar, buscar) -> DUI/RFC/pasaporte
[5] Historial de operaciones             -> folios, montos y clientes
[6] Cierre de caja del día               -> arqueo por divisa + reporte
[0] Salir
```

Los datos se **persisten automáticamente** en `data/`:
`monedas.json`, `clientes.json` y `transacciones.json` (se crean al primer
arranque y están excluidos del repositorio). Los tickets van a
`data/Tickets/` y los arqueos a `data/Reportes/`.

## 3. Estructura del proyecto (aislamiento por carpetas)

```
proyecto-equipo-1/           <-- repositorio único del equipo
├── .gitignore
├── README.md
├── src/
│   ├── main.py              # Punto de entrada (conecta las capas)
│   ├── domain/              # CÉLULA 1 - Modelo de Dominio (POO pura)
│   │   ├── models.py        # Moneda, Cliente, Transaccion, CierreCaja
│   │   └── exceptions.py    # Excepciones personalizadas de negocio
│   ├── services/            # CÉLULA 2 - Servicios y Datos
│   │   ├── catalogo.py      # Divisas iniciales por defecto (datos semilla)
│   │   ├── data_manager.py  # Persistencia JSON (guardar / leer)
│   │   └── app_service.py   # Casos de uso: AppService (fachada única)
│   └── ui/                  # CÉLULA 3 - Presentación / CLI
│       ├── cli_interface.py # Menú de consola (MenuCLI, entrega formal)
│       └── gui_app.py       # GUI tkinter (demostración del Demo Day)
└── tests/
    ├── test_domain.py       # Pruebas unitarias de dominio
    └── test_services.py     # Pruebas de casos de uso y persistencia
```

## 4. Células de desarrollo

| Célula | Responsabilidad | Sólo edita |
|--------|-----------------|------------|
| Célula 1 · Dominio POO (3) | Diseño de clases, validaciones, reglas de negocio | `src/domain/*` |
| Célula 2 · Servicios y Datos (3) | Lógica de casos de uso, persistencia | `src/services/*` |
| Célula 3 · Interfaz/CLI (3) | Flujo visual, menú, integración | `src/ui/*` y `src/main.py` |
| GitMaster / Integrador (1) | Gestiona GitHub, valida ejecución, aprueba Merges | `main` (sólo merge) |

**Reglas de juego**

1. **Un solo repositorio** por equipo (proporcionado por el docente).
2. **Nadie hace commits directos en `main`**, excepto merges aprobados.
3. Desarrollo por ramas `feature/<celula>-<historia>` (p.ej.
   `feature/dominio-monedas`, `feature/servicios-operaciones`,
   `feature/ui-menu`).
4. **IA como copiloto**: cada PR documenta el prompt principal utilizado.
5. **Validación humana**: no se mergea código de IA sin ejecutarlo y
   probarlo localmente (ver `tests/` y comprobación manual).

## 5. Prompt base de IA (Human-AI Co-creation)

Cada célula copia su prompt en la sección *"Prompt de IA Utilizado"* de su
Pull Request.

**Prompt base (raíz, para todas las células):**

> "Actúa como un desarrollador senior en Python. Para el proyecto
> 'CasaDeCambio' (servicio profesional de divisas) con arquitectura en
> capas (domain/services/ui) y POO: genera código con type hints,
> docstrings en español, excepciones personalizadas y sin dependencias
> externas, respetando el aislamiento de carpetas del equipo."

**Prompt Célula 1 (Dominio):**

> "Crea `src/domain/models.py` con las clases puras `Moneda` (dataclass
> inmutable, código de 3 letras, compra < venta, USD siempre a 1.0),
> `Cliente`, `Transaccion` (folio, fecha, tipo COMPRA/VENTA, tasas y
> montos) y `CierreCaja` (arqueo por divisa), más `exceptions.py`. La
> capa de dominio NO debe importar nada de services ni de ui."

**Prompt Célula 2 (Servicios):**

> "Implementa en `src/services/` el catálogo de divisas (semilla: USD
> base, EUR, GBP, MXN, CAD, JPY), la persistencia JSON
> (`data_manager.py`) y los casos de uso (`app_service.py`): editar
> tasas, registrar/buscar clientes, comprar y vender contra USD con su
> ticket, historial y cierre de caja, más una fachada `AppService`."

**Prompt Célula 3 (Interfaz):**

> "Crea el menú de consola `src/ui/cli_interface.py` con `MenuCLI` que
> consuma la fachada `AppService` (cotizaciones, operación con ticket,
> tasas, clientes, historial y cierre de caja) y ajusta `src/main.py`
> para que las importaciones al paquete `src` funcionen: `from
> src.ui.cli_interface import MenuCLI`."

## 6. Evidencia esperada del Demo Day

- `python src/main.py` de punta a punta (5 historias funcionando).
- Historial de commits por rama y PRs con merges aprobados por el GitMaster.
- Salida de las pruebas: `python -m unittest discover -s tests -v`.