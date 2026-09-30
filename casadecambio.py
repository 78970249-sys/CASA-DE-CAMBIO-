# -*- coding: utf-8 -*-
"""CasaDeCambio — Servicio Profesional de Divisas (archivo único).

Versión autocontenida del proyecto "CasaDeCambio": modelo de dominio,
servicios y datos, interfaz de consola y una GUI demo (tkinter), todo en
un solo archivo para ejecutar o subir sin estructura de carpetas.

Uso:
    python casadecambio.py          -> interfaz gráfica (tkinter)
    python casadecambio.py cli      -> menú de consola

No requiere dependencias externas: solo la biblioteca estándar.
Los datos se guardan en la carpeta data/ junto a este archivo.

Estructura interna (por capas):
    - Célula 1 · Dominio POO  (modelos + reglas de negocio)
    - Célula 2 · Servicios    (casos de uso + persistencia JSON)
    - Célula 3 · Interfaz     (CLI de consola y GUI tkinter)
"""

from __future__ import annotations

import json
import os
import re
import sys
import tkinter as tk
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import FrozenSet, List, Optional, Union


# ======================================================================
# CÉLULA 1 · DOMINIO POO
# ======================================================================

CODIGO_BASE: str = "USD"
"""Código de la moneda local (dólar estadounidense)."""

SIN_CLIENTE: str = "PÚBLICO (sin cliente)"
"""Etiqueta usada cuando una operación no se registra a nombre de nadie."""

TIPOS_OPERACION: FrozenSet[str] = frozenset({"COMPRA", "VENTA"})
"""Operaciones permitidas: la casa compra divisa o la casa vende divisa."""


# ----------------------------------------------------------------------
# Excepciones de negocio
# ----------------------------------------------------------------------
class DivisasError(Exception):
    """Error base de la casa de cambio."""


class MonedaInvalidaError(DivisasError):
    """Una moneda no cumple las reglas de la plaza."""


class TasaInvalidaError(DivisasError):
    """Una tasa de cambio es inválida (negativa, nula o sin spread)."""


class ClienteInvalidoError(DivisasError):
    """Un cliente no cumple los campos mínimos."""


class ClienteDuplicadoError(DivisasError):
    """Ya existe un cliente con el mismo documento."""


class ClienteNoEncontradoError(DivisasError):
    """No existe un cliente con ese identificador."""


class MonedaNoEncontradaError(DivisasError):
    """No existe una moneda con ese código."""


class TransaccionInvalidaError(DivisasError):
    """Operación de compra/venta inválida (monto, moneda base, etc.)."""


# ----------------------------------------------------------------------
# Moneda
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Moneda:
    """Divisa cotizada por la casa de cambio.

    Valores:
        compra: dólares que la casa paga por 1 unidad de esta divisa.
        venta: dólares que la casa cobra por 1 unidad de esta divisa.

    Reglas:
        - el código son 3 letras mayúsculas;
        - compra y venta deben ser positivas;
        - para divisas distintas de USD, venta debe ser mayor que compra
          (spread positivo: así la casa gana en cada lado de la mesa).
    """

    codigo: str
    nombre: str
    simbolo: str
    compra: float
    venta: float

    def __post_init__(self) -> None:
        codigo = self.codigo.strip().upper()
        if not (len(codigo) == 3 and codigo.isalpha()):
            raise MonedaInvalidaError(
                f"El código '{self.codigo}' debe tener 3 letras."
            )
        if not self.nombre.strip():
            raise MonedaInvalidaError("La moneda debe tener un nombre.")
        if not self.simbolo.strip():
            raise MonedaInvalidaError("La moneda debe tener un símbolo.")
        if self.compra <= 0 or self.venta <= 0:
            raise TasaInvalidaError(
                "Compra y venta deben ser mayores que cero."
            )
        if codigo != CODIGO_BASE and self.venta <= self.compra:
            raise TasaInvalidaError(
                f"En '{codigo}' la venta ({self.venta}) debe superar la "
                f"compra ({self.compra}) para dejar margen."
            )
        if codigo == CODIGO_BASE and (
            self.compra != 1.0 or self.venta != 1.0
        ):
            raise TasaInvalidaError(
                "La moneda base (USD) siempre cotiza 1.0000 a 1.0000."
            )

        object.__setattr__(self, "codigo", codigo)
        object.__setattr__(self, "compra", round(self.compra, 4))
        object.__setattr__(self, "venta", round(self.venta, 4))

    @property
    def es_base(self) -> bool:
        return self.codigo == CODIGO_BASE

    def __str__(self) -> str:
        return (
            f"{self.codigo} {self.nombre} | "
            f"C {self.compra:.4f} / V {self.venta:.4f}"
        )


# ----------------------------------------------------------------------
# Cliente
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Cliente:
    """Cliente registrado de la casa de cambio."""

    codigo: str
    nombre: str
    documento: str
    telefono: str = ""
    email: str = ""

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise ClienteInvalidoError("El cliente debe tener un código.")
        if not self.nombre.strip():
            raise ClienteInvalidoError("El cliente debe tener un nombre.")
        if not self.documento.strip():
            raise ClienteInvalidoError(
                "El cliente debe tener un documento de identidad "
                "(DUI/RFC/pasaporte)."
            )

    def __str__(self) -> str:
        return f"{self.codigo} · {self.nombre} ({self.documento})"


# ----------------------------------------------------------------------
# Transacción
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Transaccion:
    """Operación de compra o venta de divisa ya ejecutada."""

    folio: str
    fecha: datetime
    tipo: str
    moneda: str
    moneda_nombre: str
    simbolo: str
    tasa: float
    monto_divisa: float
    monto_local: float
    cliente: str

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS_OPERACION:
            raise TransaccionInvalidaError(
                f"Tipo de operación desconocido: {self.tipo}."
            )
        if self.monto_divisa <= 0:
            raise TransaccionInvalidaError(
                "El monto de la divisa debe ser mayor que cero."
            )

    def __str__(self) -> str:
        return (
            f"{self.folio} | {self.fecha:%Y-%m-%d %H:%M} | {self.tipo} "
            f"{self.monto_divisa:.2f} {self.moneda} | "
            f"{self.monto_local:.2f} USD"
        )


def generar_ticket(transaccion: Transaccion) -> str:
    """Devuelve el texto listo para imprimir del ticket de la operación."""
    if transaccion.tipo == "COMPRA":
        operacion = (
            "COMPRA DE DIVISA\n"
            f"La casa compró {transaccion.monto_divisa:.2f} "
            f"{transaccion.moneda} y entregó al cliente "
            f"{transaccion.monto_local:.2f} USD"
        )
    else:
        operacion = (
            "VENTA DE DIVISA\n"
            f"La casa vendió {transaccion.monto_divisa:.2f} "
            f"{transaccion.moneda} y recibió del cliente "
            f"{transaccion.monto_local:.2f} USD"
        )
    linea = "=" * 44
    return "\n".join([
        linea,
        "Casa de Cambio · Ticket de operación",
        linea,
        f"Folio:      {transaccion.folio}",
        f"Fecha:      {transaccion.fecha:%Y-%m-%d %H:%M}",
        f"Cliente:    {transaccion.cliente}",
        linea,
        operacion,
        linea,
        f"Divisa:     {transaccion.moneda} "
        f"({transaccion.moneda_nombre})",
        f"Tasa:       {transaccion.tasa:.4f} US$ por unidad",
        f"Total US$:  {transaccion.monto_local:.2f}",
        linea,
        "Gracias por operar con nosotros.",
        linea,
    ])


# ----------------------------------------------------------------------
# Cierre de caja (arqueo)
# ----------------------------------------------------------------------
@dataclass
class MovimientosMoneda:
    """Movimientos de una divisa en el arqueo del día."""

    codigo: str
    nombre: str
    compradas: float = 0.0
    vendidas: float = 0.0
    usd_pagados: float = 0.0
    usd_recibidos: float = 0.0

    @property
    def posicion(self) -> float:
        """Unidades de divisa que la casa conserva (compradas - vendidas)."""
        return round(self.compradas - self.vendidas, 4)

    @property
    def resultado_usd(self) -> float:
        """Margen en dólares de esta divisa (recibido - pagado)."""
        return round(self.usd_recibidos - self.usd_pagados, 2)


@dataclass
class CierreCaja:
    """Arqueo consolidado de un día de operaciones."""

    fecha: date
    movimientos: List[MovimientosMoneda] = field(default_factory=list)
    transacciones: int = 0

    @property
    def total_usd_pagado(self) -> float:
        return round(sum(m.usd_pagados for m in self.movimientos), 2)

    @property
    def total_usd_recibido(self) -> float:
        return round(sum(m.usd_recibidos for m in self.movimientos), 2)

    @property
    def resultado_del_dia(self) -> float:
        """Utilidad/margen del día: recibido menos pagado."""
        return round(self.total_usd_recibido - self.total_usd_pagado, 2)

    def texto(self) -> str:
        """Reporte del arqueo listo para imprimir o guardar."""
        linea = "=" * 48
        encabezado = [
            linea,
            f"ARQUEO DE CAJA · {self.fecha:%Y-%m-%d}",
            f"Operaciones del día: {self.transacciones}",
            linea,
            f"{'Divisa':<6} {'Compradas':>10} {'Vendidas':>10} "
            f"{'US$ Pag':>9} {'US$ Rec':>9} {'Resultado':>10}",
        ]
        filas = [
            f"{m.codigo:<6} {m.compradas:>10.2f} {m.vendidas:>10.2f} "
            f"{m.usd_pagados:>9.2f} {m.usd_recibidos:>9.2f} "
            f"{m.resultado_usd:>10.2f}"
            for m in self.movimientos
        ]
        suma = [
            linea,
            f"TOTAL US$ pagado por divisa:   {self.total_usd_pagado:,.2f}",
            f"TOTAL US$ recibido por venta:  {self.total_usd_recibido:,.2f}",
            f"MARGEN DEL DÍA (resultado):    {self.resultado_del_dia:,.2f}",
            linea,
        ]
        return "\n".join(encabezado + filas + suma)


# ======================================================================
# CÉLULA 2 · SERVICIOS Y DATOS
# ======================================================================

# --- Catálogo inicial de divisas --------------------------------------
_MONEDAS_INICIALES: List[Moneda] = [
    Moneda("EUR", "Euro", "€", 1.0800, 1.2000),
    Moneda("GBP", "Libra esterlina", "£", 1.2600, 1.4000),
    Moneda("MXN", "Peso mexicano", "$", 0.0480, 0.0580),
    Moneda("CAD", "Dólar canadiense", "C$", 0.7300, 0.8100),
    Moneda("JPY", "Yen japonés", "¥", 0.0063, 0.0074),
]


def monedas_iniciales() -> List[Moneda]:
    """Devuelve la lista inicial (USD base siempre presente)."""
    return [
        Moneda("USD", "Dólar estadounidense", "US$", 1.0000, 1.0000),
        *_MONEDAS_INICIALES,
    ]


# --- Persistencia ------------------------------------------------------
Ruta = Union[str, Path]


def _default_dir() -> Path:
    return Path(__file__).resolve().parent / "data"


def _aplicar(diccionario: dict, objeto) -> dict:
    """Vuelca un dataclass a dict respetando fechas en ISO."""
    datos = dict(diccionario)
    for clave, valor in datos.items():
        if isinstance(valor, datetime):
            datos[clave] = valor.isoformat(sep=" ", timespec="seconds")
        elif isinstance(valor, date):
            datos[clave] = valor.isoformat()
    return datos


class CasaDataManager:
    """Lee y escribe las colecciones de la casa de cambio."""

    def __init__(self, base: Ruta | None = None) -> None:
        base = Path(base) if base else _default_dir()
        base.mkdir(parents=True, exist_ok=True)
        self._p_monedas = base / "monedas.json"
        self._p_clientes = base / "clientes.json"
        self._p_trans = base / "transacciones.json"
        self._tickets = base / "Tickets"
        self._reportes = base / "Reportes"

    def cargar_monedas(self) -> List[Moneda]:
        if not self._p_monedas.exists():
            iniciales = monedas_iniciales()
            self.guardar_monedas(iniciales)
            return iniciales
        with self._p_monedas.open(encoding="utf-8") as fh:
            return [Moneda(**d) for d in json.load(fh)]

    def guardar_monedas(self, monedas: List[Moneda]) -> None:
        datos = [_aplicar(vars(m), m) for m in monedas]
        self._p_monedas.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def cargar_clientes(self) -> List[Cliente]:
        if not self._p_clientes.exists():
            self.guardar_clientes([])
            return []
        with self._p_clientes.open(encoding="utf-8") as fh:
            return [Cliente(**d) for d in json.load(fh)]

    def guardar_clientes(self, clientes: List[Cliente]) -> None:
        datos = [_aplicar(vars(c), c) for c in clientes]
        self._p_clientes.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def cargar_transacciones(self) -> List[Transaccion]:
        if not self._p_trans.exists():
            self.guardar_transacciones([])
            return []
        trans = []
        with self._p_trans.open(encoding="utf-8") as fh:
            for d in json.load(fh):
                d["fecha"] = datetime.fromisoformat(d["fecha"])
                trans.append(Transaccion(**d))
        return trans

    def guardar_transacciones(self, trans: List[Transaccion]) -> None:
        datos = [_aplicar(vars(t), t) for t in trans]
        self._p_trans.write_text(
            json.dumps(datos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def guardar_ticket(self, ticket: str, transaccion: Transaccion) -> Path:
        self._tickets.mkdir(parents=True, exist_ok=True)
        ruta = self._tickets / f"{transaccion.folio}.txt"
        ruta.write_text(ticket, encoding="utf-8")
        return ruta

    def guardar_reporte(self, texto: str, dia: date) -> Path:
        self._reportes.mkdir(parents=True, exist_ok=True)
        ruta = self._reportes / f"arqueo_{dia:%Y%m%d}.txt"
        ruta.write_text(texto, encoding="utf-8")
        return ruta


# --- Casos de uso (fachada) --------------------------------------------
_NUM = r"^\d+(\.\d{1,2})?$"


class AppService:
    """Fachada de casos de uso de la casa de cambio."""

    def __init__(self, ruta_datos: Optional[str] = None) -> None:
        self._data = CasaDataManager(ruta_datos)
        self._monedas: List[Moneda] = self._data.cargar_monedas()
        self._clientes: List[Cliente] = self._data.cargar_clientes()
        self._transacciones: List[Transaccion] = \
            self._data.cargar_transacciones()

    # --- Acceso a colecciones (copias de seguridad) ----
    @property
    def monedas(self) -> List[Moneda]:
        return list(self._monedas)

    @property
    def clientes(self) -> List[Cliente]:
        return list(self._clientes)

    @property
    def transacciones(self) -> List[Transaccion]:
        return list(self._transacciones)

    def obtener_moneda(self, codigo: str) -> Moneda:
        busqueda = codigo.strip().upper()
        for moneda in self._monedas:
            if moneda.codigo == busqueda:
                return moneda
        raise MonedaNoEncontradaError(
            f"No existe la moneda '{codigo}' en la cotización."
        )

    # --- Tasas y monedas ----
    def actualizar_tasa(self, codigo: str, compra: float,
                        venta: float) -> Moneda:
        """Actualiza la cotización de una divisa (compra y venta)."""
        vigente = self.obtener_moneda(codigo)
        nueva = Moneda(vigente.codigo, vigente.nombre, vigente.simbolo,
                       compra, venta)
        self._reemplazar_moneda(nueva)
        return nueva

    def crear_moneda(self, codigo: str, nombre: str, simbolo: str,
                     compra: float, venta: float) -> Moneda:
        codigo = codigo.strip().upper()
        if any(m.codigo == codigo for m in self._monedas):
            raise MonedaInvalidaError(
                f"Ya existe una moneda con el código '{codigo}'."
            )
        moneda = Moneda(codigo, nombre, simbolo, compra, venta)
        self._monedas.append(moneda)
        self._data.guardar_monedas(self._monedas)
        return moneda

    def eliminar_moneda(self, codigo: str) -> Moneda:
        moneda = self.obtener_moneda(codigo)
        if moneda.es_base:
            raise MonedaInvalidaError(
                "La moneda base (USD) no puede eliminarse."
            )
        tiene_historial = any(t.moneda == moneda.codigo
                              for t in self._transacciones)
        if tiene_historial:
            raise MonedaInvalidaError(
                f"'{moneda.codigo}' tiene operaciones en el historial; "
                f"no puede eliminarse (solo desactivar tasas)."
            )
        self._monedas.remove(moneda)
        self._data.guardar_monedas(self._monedas)
        return moneda

    def _reemplazar_moneda(self, moneda: Moneda) -> None:
        for i, actual in enumerate(self._monedas):
            if actual.codigo == moneda.codigo:
                self._monedas[i] = moneda
                break
        self._data.guardar_monedas(self._monedas)

    # --- Clientes ----
    def crear_cliente(self, nombre: str, documento: str, telefono: str = "",
                      email: str = "") -> Cliente:
        nombre = nombre.strip()
        documento = documento.strip().upper()
        if not nombre or not documento:
            raise ClienteInvalidoError(
                "Nombre y documento del cliente son obligatorios."
            )
        for cliente in self._clientes:
            if cliente.documento.upper() == documento:
                raise ClienteDuplicadoError(
                    f"Ya existe un cliente con el documento '{documento}'."
                )
        codigo = f"CLI-{len(self._clientes) + 1:04d}"
        cliente = Cliente(codigo, nombre, documento, telefono.strip(),
                          email.strip())
        self._clientes.append(cliente)
        self._data.guardar_clientes(self._clientes)
        return cliente

    def buscar_clientes(self, texto: str) -> List[Cliente]:
        """Busca por código, nombre o documento (insensible a mayúsculas)."""
        criterio = texto.strip().lower()
        if not criterio:
            return list(self._clientes)
        return [
            c for c in self._clientes
            if criterio in c.nombre.lower()
            or criterio in c.documento.lower()
            or criterio in c.codigo.lower()
        ]

    def obtener_cliente_por_documento(self,
                                      documento: str) -> Optional[Cliente]:
        busqueda = documento.strip().upper()
        return next(
            (c for c in self._clientes if c.documento.upper() == busqueda),
            None,
        )

    # --- Operaciones de compra/venta ----
    def comprar(self, codigo_moneda: str, monto_divisa: float,
                cliente: Optional[Cliente] = None) -> Transaccion:
        """La casa compra divisa: paga ``monto * tasa_compra`` en USD."""
        return self._ejecutar(codigo_moneda, monto_divisa, "COMPRA", cliente)

    def vender(self, codigo_moneda: str, monto_divisa: float,
               cliente: Optional[Cliente] = None) -> Transaccion:
        """La casa vende divisa: recibe ``monto * tasa_venta`` en USD."""
        return self._ejecutar(codigo_moneda, monto_divisa, "VENTA", cliente)

    def _ejecutar(self, codigo_moneda: str, monto_divisa: float, tipo: str,
                  cliente: Optional[Cliente]) -> Transaccion:
        moneda = self.obtener_moneda(codigo_moneda)
        if moneda.es_base:
            raise TransaccionInvalidaError(
                "No se puede comprar/vender la moneda base (USD)."
            )
        if not isinstance(monto_divisa, (int, float)):
            raise TransaccionInvalidaError("El monto debe ser un número.")
        monto = round(float(monto_divisa), 2)
        if monto <= 0:
            raise TransaccionInvalidaError(
                "El monto de la divisa debe ser mayor que cero."
            )
        tasa = moneda.compra if tipo == "COMPRA" else moneda.venta
        local = round(monto * tasa, 2)
        nombre_cliente = cliente.nombre if cliente else SIN_CLIENTE

        folio = self._nuevo_folio()
        transaccion = Transaccion(
            folio=folio,
            fecha=datetime.now(),
            tipo=tipo,
            moneda=moneda.codigo,
            moneda_nombre=moneda.nombre,
            simbolo=moneda.simbolo,
            tasa=tasa,
            monto_divisa=monto,
            monto_local=local,
            cliente=nombre_cliente,
        )
        self._transacciones.append(transaccion)
        self._data.guardar_transacciones(self._transacciones)
        return transaccion

    def _nuevo_folio(self) -> str:
        hoy = date.today()
        del_dia = [t for t in self._transacciones if t.fecha.date() == hoy]
        return f"TX-{hoy:%Y%m%d}-{len(del_dia) + 1:04d}"

    # --- Tickets y cierre de caja ----
    def ticket(self, transaccion: Transaccion) -> str:
        return generar_ticket(transaccion)

    def guardar_ticket(self, transaccion: Transaccion) -> str:
        """Guarda el ticket y devuelve la ruta del archivo generado."""
        return str(self._data.guardar_ticket(
            generar_ticket(transaccion), transaccion))

    def generar_arqueo(self, dia: Optional[date] = None) -> CierreCaja:
        """Arqueo (cierre de caja) de un día; por defecto hoy."""
        dia = dia or date.today()
        del_dia = [t for t in self._transacciones if t.fecha.date() == dia]
        movimientos: dict[str, MovimientosMoneda] = {}
        for t in del_dia:
            item = movimientos.setdefault(t.moneda, MovimientosMoneda(
                codigo=t.moneda, nombre=t.moneda_nombre))
            if t.tipo == "COMPRA":
                item.compradas += t.monto_divisa
                item.usd_pagados += t.monto_local
            else:  # VENTA
                item.vendidas += t.monto_divisa
                item.usd_recibidos += t.monto_local
        return CierreCaja(
            fecha=dia,
            movimientos=sorted(movimientos.values(),
                               key=lambda m: m.codigo),
            transacciones=len(del_dia),
        )

    def guardar_arqueo(self, dia: Optional[date] = None) -> str:
        """Guarda el reporte de arqueo y devuelve la ruta del archivo."""
        arqueo = self.generar_arqueo(dia)
        return str(self._data.guardar_reporte(arqueo.texto(), arqueo.fecha))

    # --- Utilidades de entrada ----
    @staticmethod
    def validar_monto(texto: str) -> float:
        """Valida y convierte un monto escrito por el usuario.

        Acepta coma o punto como separador decimal (ej. "150,50").
        """
        texto = texto.strip().replace(",", ".")
        texto = texto.replace(" ", "")
        if not re.fullmatch(_NUM, texto):
            raise TransaccionInvalidaError(
                "Monto inválido: usa números positivos con hasta 2 "
                "decimales (ej. 150.00)."
            )
        return float(texto)


# ======================================================================
# CÉLULA 3 · INTERFAZ (CLI y GUI)
# ======================================================================

# --- Menú de consola ------------------------------------------------
class MenuCLI:
    """Menú interactivo de consola para el operador de la casa."""

    def __init__(self, servicio: AppService) -> None:
        self._s = servicio

    def ejecutar(self) -> None:
        self._cabecera()
        while True:
            opcion = self._leer_opcion()
            if opcion == "0":
                print("\nGracias por usar CasaDeCambio. Hasta pronto.")
                break
            if opcion == "1":
                self._cotizaciones()
            elif opcion == "2":
                self._operacion()
            elif opcion == "3":
                self._actualizar_tasas()
            elif opcion == "4":
                self._gestion_clientes()
            elif opcion == "5":
                self._historial()
            elif opcion == "6":
                self._cierre_de_caja()

    @staticmethod
    def _cabecera() -> None:
        print("=" * 56)
        print("CASA DE CAMBIO · Servicio profesional de divisas")
        print("Moneda local: USD (dólar estadounidense)")
        print("=" * 56)

    def _leer_opcion(self) -> str:
        print()
        print("[1] Ver cotizaciones")
        print("[2] Operación de compra / venta")
        print("[3] Actualizar tasas o monedas")
        print("[4] Clientes (listar, registrar, buscar)")
        print("[5] Historial de operaciones")
        print("[6] Cierre de caja del día")
        print("[0] Salir")
        opcion = input("Elige una opción: ").strip()
        if opcion not in {"0", "1", "2", "3", "4", "5", "6"}:
            print("Opción no válida. Intenta de nuevo.")
            return self._leer_opcion()
        return opcion

    def _cotizaciones(self) -> None:
        print("\n=== COTIZACIONES DE HOY (US$ por unidad) ===")
        print(f"{'Divisa':<7} {'Nombre':<22} {'Compra':>9} {'Venta':>9}")
        for m in self._s.monedas:
            print(f"{m.codigo:<7} {m.nombre:<22} {m.compra:>8.4f} "
                  f"{m.venta:>8.4f}")

    def _operacion(self) -> None:
        self._cotizaciones()
        tipo = self._elegir("¿Qué hará la casa?", ("COMPRA", "VENTA"))
        divisas = [m for m in self._s.monedas if not m.es_base]
        codigo = self._elegir_por_codigo(divisas)
        monto = self._leer_monto()
        cliente = self._elegir_cliente()
        try:
            if tipo == "COMPRA":
                transaccion = self._s.comprar(codigo, monto, cliente)
            else:
                transaccion = self._s.vender(codigo, monto, cliente)
        except Exception as err:
            print(f"\nError: {err}")
            return
        self._mostrar_ticket(transaccion)

    def _actualizar_tasas(self) -> None:
        self._cotizaciones()
        print()
        print("[A] Actualizar tasa de una moneda")
        print("[B] Agregar moneda")
        print("[C] Eliminar moneda")
        sub = input("Elige (A/B/C, vacío para volver): ").strip().upper()
        if sub == "":
            return
        if sub == "A":
            self._editar_tasa()
        elif sub == "B":
            self._agregar_moneda()
        elif sub == "C":
            self._eliminar_moneda()
        else:
            print("Opción no válida.")

    def _editar_tasa(self) -> None:
        divisas = [m for m in self._s.monedas if not m.es_base]
        codigo = self._elegir_por_codigo(divisas)
        compra = self._leer_numero("Nuevo tipo de COMPRA: ")
        venta = self._leer_numero("Nuevo tipo de VENTA: ")
        try:
            moneda = self._s.actualizar_tasa(codigo, compra, venta)
        except Exception as err:
            print(f"\nError: {err}")
        else:
            print(f"Tasa actualizada: {moneda}")

    def _agregar_moneda(self) -> None:
        codigo = input("Código (3 letras): ").strip()
        nombre = input("Nombre de la moneda: ").strip()
        simbolo = input("Símbolo: ").strip()
        compra = self._leer_numero("Tipo de COMPRA: ")
        venta = self._leer_numero("Tipo de VENTA: ")
        try:
            moneda = self._s.crear_moneda(codigo, nombre, simbolo,
                                          compra, venta)
        except Exception as err:
            print(f"\nError: {err}")
        else:
            print(f"Moneda agregada: {moneda}")

    def _eliminar_moneda(self) -> None:
        divisas = [m for m in self._s.monedas if not m.es_base]
        codigo = self._elegir_por_codigo(divisas)
        if input(f"¿Eliminar '{codigo}'? (si/no): ").lower() != "si":
            print("Cancelado.")
            return
        try:
            moneda = self._s.eliminar_moneda(codigo)
        except Exception as err:
            print(f"\nError: {err}")
        else:
            print(f"Moneda eliminada: {moneda.codigo}")

    def _gestion_clientes(self) -> None:
        print("\n=== CLIENTES ===")
        print("[1] Listar todos")
        print("[2] Registrar nuevo")
        print("[3] Buscar por nombre/documento/código")
        opcion = input("Elige (vacío para volver): ").strip()
        if opcion == "1":
            self._listar_clientes()
        elif opcion == "2":
            self._registrar_cliente()
        elif opcion == "3":
            self._buscar_clientes()
        else:
            return

    def _listar_clientes(self) -> None:
        self._pintar_clientes(self._s.clientes)

    @staticmethod
    def _pintar_clientes(clientes: List[Cliente]) -> None:
        if not clientes:
            print("\nNo hay clientes registrados.")
            return
        print("\n" + f"{'Código':<9} {'Nombre':<32} {'Documento':<14}")
        for c in clientes:
            print(f"{c.codigo:<9} {c.nombre:<32} {c.documento:<14}")

    def _registrar_cliente(self) -> None:
        nombre = input("Nombre completo: ").strip()
        documento = input("Documento (DUI/RFC/pasaporte): ").strip()
        telefono = input("Teléfono (opcional): ").strip()
        email = input("Correo (opcional): ").strip()
        try:
            cliente = self._s.crear_cliente(nombre, documento,
                                            telefono, email)
        except Exception as err:
            print(f"\nError: {err}")
        else:
            print(f"\nCliente registrado: {cliente}")

    def _buscar_clientes(self) -> None:
        texto = input("Buscar: ").strip()
        self._pintar_clientes(self._s.buscar_clientes(texto))

    def _historial(self) -> None:
        lista = list(reversed(self._s.transacciones))
        if not lista:
            print("\nAún no hay operaciones registradas.")
            return
        print("\n=== HISTORIAL DE OPERACIONES ===")
        print(f"{'Folio':<18} {'Fecha':<17} {'Tipo':<7} {'Divisa':<7} "
              f"{'Monto':>10} {'US$':>10} {'Cliente':<10}")
        for t in lista:
            print(f"{t.folio:<18} {t.fecha:%Y-%m-%d %H:%M} {t.tipo:<7} "
                  f"{t.moneda:<7} {t.monto_divisa:>9.2f} "
                  f"{t.monto_local:>9.2f} {t.cliente[:10]:<10}")

    def _cierre_de_caja(self) -> None:
        try:
            arqueo = self._s.generar_arqueo()
        except Exception as err:
            print(f"\nError: {err}")
            return
        print("\n" + arqueo.texto())
        if input("¿Guardar reporte en data/Reportes/? (s/n): ").lower() == "s":
            ruta = self._s.guardar_arqueo()
            print(f"Reporte guardado en {ruta}")

    def _mostrar_ticket(self, transaccion: Transaccion) -> None:
        print("\n" + self._s.ticket(transaccion))
        if input("¿Guardar ticket (data/Tickets/)? (s/n): ").lower() == "s":
            print(f"Ticket guardado en {self._s.guardar_ticket(transaccion)}")

    def _elegir(self, pregunta: str, opciones) -> str:
        for i, opcion in enumerate(opciones, start=1):
            print(f"[{i}] {opcion}")
        sel = input(f"{pregunta} (1-{len(opciones)}): ").strip()
        try:
            return opciones[int(sel) - 1]
        except (ValueError, IndexError):
            print("Selección no válida.")
            return self._elegir(pregunta, opciones)

    def _elegir_por_codigo(self, monedas: List[Moneda]) -> str:
        print()
        for m in monedas:
            print(f"  {m.codigo}  {m.nombre}  (C {m.compra:.4f} / "
                  f"V {m.venta:.4f})")
        codigo = input("Código de la divisa: ").strip().upper()
        try:
            self._s.obtener_moneda(codigo)
            return codigo
        except Exception:
            print("Código no válido.")
            return self._elegir_por_codigo(monedas)

    def _leer_monto(self) -> float:
        try:
            return self._s.validar_monto(input("Monto en la divisa: "))
        except Exception as err:
            print(err)
            return self._leer_monto()

    @staticmethod
    def _leer_numero(pregunta: str) -> float:
        texto = input(pregunta).strip().replace(",", ".")
        try:
            valor = float(texto)
        except ValueError:
            print("Número no válido.")
            return MenuCLI._leer_numero(pregunta)
        return valor

    def _elegir_cliente(self) -> Optional[Cliente]:
        print()
        if input("¿Registrar la operación a un cliente? (s/n): ").lower() != "s":
            return None
        documento = input(
            "Documento del cliente (vacío = buscar por nombre): ").strip()
        cliente = None
        if documento:
            cliente = self._s.obtener_cliente_por_documento(documento)
        if cliente is None:
            encontrados = self._s.buscar_clientes(
                documento or input("Nombre/código: ").strip())
            self._pintar_clientes(encontrados)
            if not encontrados:
                print("No se encontró el cliente.")
                return None
            if len(encontrados) == 1:
                cliente = encontrados[0]
            else:
                pos = self._elegir("Selecciona el cliente", encontrados)
                cliente = pos if isinstance(pos, Cliente) else None
        return cliente


# --- GUI (tkinter) ------------------------------------------------------
COLOR_FONDO = "#0b1f3a"
COLOR_PANEL = "#12284a"
COLOR_ACENTO = "#24c6dc"
COLOR_DORADO = "#f7b731"
COLOR_TEXTO = "#eaf2fb"
COLOR_VERDE = "#2dd4a7"
COLOR_ROJO = "#ff6b6b"
FUENTE_TITULO = ("Segoe UI", 20, "bold")
FUENTE_SUB = ("Segoe UI", 11)
FUENTE_TEXTO = ("Segoe UI", 10)
FUENTE_MONO = ("Consolas", 9)


class CasaDeCambioApp:
    """Ventana principal de la casa de cambio (demo tkinter)."""

    def __init__(self, servicio: AppService) -> None:
        self._s = servicio
        self._raiz = tk.Tk()
        self._raiz.title("CasaDeCambio · Servicio profesional de divisas")
        self._raiz.geometry("1080x680")
        self._raiz.configure(bg=COLOR_FONDO)
        self._tick_reloj()

        self._monedas: List[Moneda] = self._s.monedas
        self._clientes: List[Cliente] = self._s.clientes
        self._ultima_tx = None

        self._construir_estilos()
        self._construir_cabecera()
        self._construir_pestanas()
        self.refrescar_todo()

    def _tick_reloj(self) -> None:
        ahora = datetime.now()
        if hasattr(self, "_lbl_reloj"):
            self._lbl_reloj.config(
                text=f"{ahora:%Y-%m-%d}  {ahora:%H:%M:%S}")
        self._raiz.after(1000, self._tick_reloj)

    def _construir_estilos(self) -> None:
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("TNotebook", background=COLOR_FONDO,
                         borderwidth=0)
        estilo.configure("TNotebook.Tab", font=FUENTE_SUB,
                         padding=(18, 8), background=COLOR_PANEL,
                         foreground=COLOR_TEXTO)
        estilo.map("TNotebook.Tab",
                   background=[("selected", COLOR_ACENTO)],
                   foreground=[("selected", "#04203a")])

    def _construir_cabecera(self) -> None:
        marco = tk.Frame(self._raiz, bg=COLOR_FONDO)
        marco.pack(fill=tk.X, padx=18, pady=(14, 4))
        tk.Label(marco, text="CasaDeCambio", bg=COLOR_FONDO,
                 fg=COLOR_DORADO, font=FUENTE_TITULO).pack(side=tk.LEFT)
        tk.Label(marco, text="Divisas contra USD", bg=COLOR_FONDO,
                 fg=COLOR_ACENTO, font=FUENTE_SUB)\
            .pack(side=tk.LEFT, padx=(12, 0), pady=(8, 0))
        self._lbl_reloj = tk.Label(marco, text="", bg=COLOR_FONDO,
                                   fg=COLOR_TEXTO, font=FUENTE_MONO)
        self._lbl_reloj.pack(side=tk.RIGHT)
        tk.Label(marco, text="Operador: mantiene sus tasas con margen "
                             "(compra < venta)", bg=COLOR_FONDO,
                 fg="#9fb3c8", font=("Segoe UI", 9))\
            .pack(side=tk.RIGHT, padx=(0, 14))

        linea = tk.Frame(self._raiz, bg=COLOR_ACENTO, height=2)
        linea.pack(fill=tk.X)

    def _construir_pestanas(self) -> None:
        self._pestanas = ttk.Notebook(self._raiz)
        self._pestanas.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 6))

        self._f_operar = self._pestana("Operar")
        self._f_tasas = self._pestana("Tasas")
        self._f_clientes = self._pestana("Clientes")
        self._f_historial = self._pestana("Historial")
        self._f_caja = self._pestana("Caja")

        self._construir_operar()
        self._construir_tasas()
        self._construir_clientes()
        self._construir_historial()
        self._construir_caja()

    def _pestana(self, titulo: str) -> tk.Frame:
        marco = tk.Frame(self._pestanas, bg=COLOR_PANEL)
        self._pestanas.add(marco, text=titulo)
        return marco

    # --- Pestana 1 · Operar ---
    def _construir_operar(self) -> None:
        izq = tk.Frame(self._f_operar, bg=COLOR_PANEL)
        izq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=16)
        der = tk.Frame(self._f_operar, bg="#0e223c")
        der.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=16, pady=16)

        tk.Label(izq, text="Nueva operación", bg=COLOR_PANEL,
                 fg=COLOR_DORADO, font=("Segoe UI", 15, "bold"))\
            .pack(anchor=tk.W)

        self._var_tipo = tk.StringVar(value="COMPRA")
        for texto, valor in (("La casa COMPRA divisa", "COMPRA"),
                             ("La casa VENDE divisa", "VENTA")):
            tk.Radiobutton(izq, text=texto, value=valor,
                           variable=self._var_tipo, bg=COLOR_PANEL,
                           fg=COLOR_TEXTO, selectcolor=COLOR_PANEL,
                           activebackground=COLOR_PANEL,
                           activeforeground=COLOR_ACENTO,
                           font=FUENTE_TEXTO)\
                .pack(anchor=tk.W, pady=3)

        tk.Label(izq, text="Divisa:", bg=COLOR_PANEL, fg=COLOR_TEXTO,
                 font=FUENTE_SUB).pack(anchor=tk.W, pady=(12, 2))
        self._cmb_operar_moneda = ttk.Combobox(
            izq, state="readonly", width=34, font=FUENTE_TEXTO)
        self._cmb_operar_moneda.pack(fill=tk.X)
        self._cmb_operar_moneda.bind("<<ComboboxSelected>>",
                                     self._pintar_tasa_operar)

        tk.Label(izq, text="Cliente:", bg=COLOR_PANEL, fg=COLOR_TEXTO,
                 font=FUENTE_SUB).pack(anchor=tk.W, pady=(12, 2))
        self._cmb_operar_cliente = ttk.Combobox(
            izq, state="readonly", width=34, font=FUENTE_TEXTO)
        self._cmb_operar_cliente.pack(fill=tk.X)

        tk.Label(izq, text="Monto en la divisa (US$ x unidad):",
                 bg=COLOR_PANEL, fg=COLOR_TEXTO, font=FUENTE_SUB)\
            .pack(anchor=tk.W, pady=(12, 2))
        self._ent_monto = tk.Entry(izq, font=("Segoe UI", 14),
                                   bg="#eaf2fb", fg="#04203a",
                                   justify=tk.RIGHT, relief=tk.FLAT)
        self._ent_monto.pack(fill=tk.X, ipady=6)
        self._ent_monto.insert(0, "100.00")

        self._lbl_tasa = tk.Label(izq, text="", bg=COLOR_PANEL,
                                  fg=COLOR_ACENTO, font=FUENTE_MONO)
        self._lbl_tasa.pack(anchor=tk.W, pady=(10, 0))

        boton = tk.Button(izq, text="EJECUTAR OPERACIÓN", bg=COLOR_ACENTO,
                          fg="#04203a", activebackground=COLOR_DORADO,
                          font=("Segoe UI", 13, "bold"), relief=tk.FLAT,
                          command=self._ejecutar_operacion, cursor="hand2")
        boton.pack(fill=tk.X, pady=(14, 0), ipady=10)

        tk.Label(der, text="Ticket / Confirmación", bg="#0e223c",
                 fg=COLOR_DORADO, font=("Segoe UI", 13, "bold"))\
            .pack(anchor=tk.W)
        self._txt_ticket = tk.Text(der, width=44, bg="#0e223c",
                                   fg=COLOR_VERDE, font=FUENTE_MONO,
                                   relief=tk.FLAT, padx=12, pady=10)
        self._txt_ticket.pack(fill=tk.BOTH, expand=True, pady=(6, 8))
        self._txt_ticket.insert(tk.END,
                                "Aquí se mostrará el ticket de la "
                                "operación.\n")
        self._txt_ticket.config(state=tk.DISABLED)

        fila = tk.Frame(der, bg="#0e223c")
        fila.pack(fill=tk.X)
        tk.Button(fila, text="Guardar ticket en data/Tickets",
                  bg=COLOR_PANEL, fg=COLOR_TEXTO, relief=tk.FLAT,
                  command=self._guardar_ticket_actual, cursor="hand2")\
            .pack(side=tk.LEFT)

    def _pintar_tasa_operar(self, _event=None) -> None:
        moneda = self._moneda_seleccionada()
        if not moneda:
            self._lbl_tasa.config(text="")
            return
        if self._var_tipo.get() == "COMPRA":
            tasa = moneda.compra
            texto = f"La casa pagará {tasa:.4f} US$ por cada {moneda.codigo}"
        else:
            tasa = moneda.venta
            texto = f"La casa cobrará {tasa:.4f} US$ por cada {moneda.codigo}"
        self._lbl_tasa.config(text=texto)

    def _moneda_seleccionada(self) -> Optional[Moneda]:
        sel = self._cmb_operar_moneda.get()
        for moneda in self._monedas:
            if f"{moneda.codigo} · {moneda.nombre}" == sel:
                return moneda
        return None

    def _cliente_seleccionado(self) -> Optional[Cliente]:
        nombre = self._cmb_operar_cliente.get().strip()
        for cliente in self._clientes:
            if cliente.codigo in nombre:
                return cliente
        return None

    def _ejecutar_operacion(self) -> None:
        moneda = self._moneda_seleccionada()
        if not moneda:
            messagebox.showerror("CasaDeCambio",
                                 "Selecciona una divisa primero.")
            return
        try:
            monto = self._s.validar_monto(self._ent_monto.get())
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        cliente = self._cliente_seleccionado()
        try:
            if self._var_tipo.get() == "COMPRA":
                tx = self._s.comprar(moneda.codigo, monto, cliente)
            else:
                tx = self._s.vender(moneda.codigo, monto, cliente)
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        self._ultima_tx = tx
        self._mostrar_ticket(tx)
        self._refrescar_historial()
        self._refrescar_caja()
        messagebox.showinfo("CasaDeCambio",
                            f"Operación registrada: folio {tx.folio}",
                            parent=self._raiz)

    def _mostrar_ticket(self, tx) -> None:
        self._txt_ticket.config(state=tk.NORMAL)
        self._txt_ticket.delete("1.0", tk.END)
        self._txt_ticket.insert(tk.END, self._s.ticket(tx))
        self._txt_ticket.config(state=tk.DISABLED)

    def _guardar_ticket_actual(self) -> None:
        if self._ultima_tx is None:
            messagebox.showinfo("CasaDeCambio",
                                "Primero ejecuta una operación.")
            return
        ruta = self._s.guardar_ticket(self._ultima_tx)
        messagebox.showinfo("CasaDeCambio",
                            f"Ticket guardado en:\n{ruta}")

    # --- Pestana 2 · Tasas ---
    def _construir_tasas(self) -> None:
        m = self._f_tasas
        tk.Label(m, text="Cotización de divisas (US$ por unidad)",
                 bg=COLOR_PANEL, fg=COLOR_DORADO,
                 font=("Segoe UI", 14, "bold")).pack(anchor=tk.W,
                                                     padx=16, pady=(12, 4))

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self._tabla_tasas = ttk.Treeview(
            contenedor, columns=("codigo", "nombre", "simbolo", "compra",
                                 "venta", "spread"),
            show="headings", height=10)
        for col, ancho in (("codigo", 70), ("nombre", 200), ("simbolo", 60),
                           ("compra", 110), ("venta", 110), ("spread", 100)):
            self._tabla_tasas.heading(col, text=col.upper(),
                                      anchor=tk.CENTER)
            self._tabla_tasas.column(col, width=ancho, anchor=tk.CENTER)
        self._tabla_tasas.tag_configure("base", background="#1c3a5e",
                                        foreground=COLOR_DORADO)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_tasas.yview)
        self._tabla_tasas.configure(yscrollcommand=scroll_y.set)
        self._tabla_tasas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        fila = tk.Frame(m, bg=COLOR_PANEL)
        fila.pack(fill=tk.X, padx=16, pady=(4, 14))
        tk.Button(fila, text="Actualizar tasa", bg=COLOR_ACENTO,
                  fg="#04203a", font=FUENTE_SUB, relief=tk.FLAT,
                  command=self._editar_tasa_gui, cursor="hand2")\
            .pack(side=tk.LEFT, padx=(0, 8), ipadx=8, ipady=5)
        tk.Button(fila, text="Agregar moneda", bg=COLOR_PANEL,
                  fg=COLOR_TEXTO, relief=tk.FLAT,
                  command=self._agregar_moneda_gui)\
            .pack(side=tk.LEFT, padx=(0, 8), ipadx=8, ipady=5)
        tk.Button(fila, text="Eliminar moneda", bg=COLOR_PANEL,
                  fg=COLOR_ROJO, relief=tk.FLAT,
                  command=self._eliminar_moneda_gui)\
            .pack(side=tk.LEFT, ipadx=8, ipady=5)

    def _editar_tasa_gui(self) -> None:
        sel = self._seleccion_tabla(self._tabla_tasas)
        if not sel:
            messagebox.showinfo("CasaDeCambio", "Selecciona una moneda.")
            return
        moneda = self._s.obtener_moneda(sel["codigo"])
        if moneda.es_base:
            messagebox.showinfo("CasaDeCambio",
                                "USD siempre cotiza 1.0000 a 1.0000.")
            return
        ventana = tk.Toplevel(self._raiz)
        ventana.title(f"Actualizar tasa {moneda.codigo}")
        ventana.configure(bg=COLOR_PANEL)
        ventana.resizable(False, False)
        entrada = {}
        cuerpo = tk.Frame(ventana)
        cuerpo.pack(padx=18, pady=14)
        tk.Label(cuerpo, text=moneda.nombre).grid(row=0, column=0,
                                                  columnspan=2)
        for i, (atr, lbl) in enumerate((("compra", "Tipo de compra"),
                                        ("venta", "Tipo de venta"))):
            tk.Label(cuerpo, text=lbl).grid(row=i + 1, column=0,
                                            sticky=tk.W, pady=3)
            entrada[lbl] = tk.Entry(cuerpo, width=16)
            entrada[lbl].insert(0, f"{getattr(moneda, atr):.4f}")
            entrada[lbl].grid(row=i + 1, column=1, padx=8, pady=3)
        t = tk.Frame(ventana)
        t.pack(pady=(0, 14))

        def guardar() -> None:
            try:
                compra = float(entrada["Tipo de compra"].get())
                venta = float(entrada["Tipo de venta"].get())
                self._s.actualizar_tasa(moneda.codigo, compra, venta)
            except Exception as err:
                messagebox.showerror("CasaDeCambio", str(err))
                return
            ventana.destroy()
            self.refrescar_todo()

        tk.Button(t, text="Guardar", command=guardar)\
            .pack(side=tk.LEFT, padx=6)
        tk.Button(t, text="Cancelar", command=ventana.destroy)\
            .pack(side=tk.LEFT, padx=6)

    def _agregar_moneda_gui(self) -> None:
        ventana = tk.Toplevel(self._raiz)
        ventana.title("Agregar moneda")
        ventana.configure(bg=COLOR_PANEL)
        ventana.resizable(False, False)
        campos = {}
        cuerpo = tk.Frame(ventana)
        cuerpo.pack(padx=18, pady=14)
        etiquetas = ["Código (3 letras)", "Nombre", "Símbolo",
                     "Tipo de compra", "Tipo de venta"]
        for fila, texto in enumerate(etiquetas):
            tk.Label(cuerpo, text=texto).grid(row=fila, column=0,
                                              sticky=tk.W, pady=3)
            campos[texto] = tk.Entry(cuerpo, width=18)
            campos[texto].grid(row=fila, column=1, padx=8, pady=3)
        t = tk.Frame(ventana)
        t.pack(pady=(0, 14))

        def guardar() -> None:
            try:
                compra = float(campos["Tipo de compra"].get())
                venta = float(campos["Tipo de venta"].get())
                self._s.crear_moneda(campos["Código (3 letras)"].get(),
                                     campos["Nombre"].get(),
                                     campos["Símbolo"].get(), compra, venta)
            except Exception as err:
                messagebox.showerror("CasaDeCambio", str(err))
                return
            ventana.destroy()
            self.refrescar_todo()

        tk.Button(t, text="Guardar", command=guardar)\
            .pack(side=tk.LEFT, padx=6)
        tk.Button(t, text="Cancelar", command=ventana.destroy)\
            .pack(side=tk.LEFT, padx=6)

    def _eliminar_moneda_gui(self) -> None:
        sel = self._seleccion_tabla(self._tabla_tasas)
        if not sel:
            messagebox.showinfo("CasaDeCambio", "Selecciona una moneda.")
            return
        if sel["codigo"] == "USD":
            messagebox.showerror("CasaDeCambio",
                                 "La moneda base no puede eliminarse.")
            return
        if not messagebox.askyesno(
                "CasaDeCambio", f"¿Eliminar {sel['codigo']} ({sel['nombre']})?"):
            return
        try:
            self._s.eliminar_moneda(sel["codigo"])
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
        else:
            self.refrescar_todo()

    # --- Pestana 3 · Clientes ---
    def _construir_clientes(self) -> None:
        m = self._f_clientes
        form = tk.Frame(m, bg=COLOR_PANEL)
        form.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(form, text="Registrar cliente", bg=COLOR_PANEL,
                 fg=COLOR_DORADO, font=("Segoe UI", 13, "bold"))\
            .grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 6))
        self._lc = {}
        for i, (clave, texto, ancho) in enumerate([
                ("nombre", "Nombre completo", 26),
                ("documento", "Documento (DUI/RFC/pasaporte)", 22),
                ("telefono", "Teléfono", 16),
                ("email", "Correo", 24)]):
            tk.Label(form, text=texto, bg=COLOR_PANEL, fg=COLOR_TEXTO,
                     font=("Segoe UI", 9)).grid(row=1, column=i * 2,
                                                sticky=tk.W, padx=(0, 4))
            self._lc[clave] = tk.Entry(form, width=ancho, bg="#eaf2fb",
                                       fg="#04203a")
            self._lc[clave].grid(row=2, column=i * 2, padx=(0, 10),
                                 sticky=tk.W)
        tk.Button(form, text="Registrar",
                  command=self._registrar_cliente_gui)\
            .grid(row=1, column=8, rowspan=2, sticky=tk.S, padx=6)
        tk.Button(form, text="Limpiar",
                  command=self._limpiar_form_cliente)\
            .grid(row=1, column=9, rowspan=2, sticky=tk.S)

        busqueda = tk.Frame(m, bg=COLOR_PANEL)
        busqueda.pack(fill=tk.X, padx=16, pady=(0, 6))
        tk.Label(busqueda, text="Buscar: ", bg=COLOR_PANEL, fg=COLOR_TEXTO)\
            .pack(side=tk.LEFT)
        self._ent_buscar = tk.Entry(busqueda, width=40, bg="#eaf2fb")
        self._ent_buscar.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(busqueda, text="Buscar", command=self._buscar_clientes_gui)\
            .pack(side=tk.LEFT)
        tk.Button(busqueda, text="Mostrar todos",
                  command=self.refrescar_todo).pack(side=tk.LEFT, padx=8)

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        self._tabla_clientes = ttk.Treeview(
            contenedor, columns=("codigo", "nombre", "documento",
                                 "telefono", "email"), show="headings")
        for col, ancho in (("codigo", 80), ("nombre", 220),
                           ("documento", 180), ("telefono", 130),
                           ("email", 200)):
            self._tabla_clientes.heading(col, text=col.upper(),
                                         anchor=tk.CENTER)
            self._tabla_clientes.column(col, width=ancho, anchor=tk.CENTER)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_clientes.yview)
        self._tabla_clientes.configure(yscrollcommand=scroll_y.set)
        self._tabla_clientes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _registrar_cliente_gui(self) -> None:
        try:
            cliente = self._s.crear_cliente(
                self._lc["nombre"].get(), self._lc["documento"].get(),
                self._lc["telefono"].get(), self._lc["email"].get())
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        self._limpiar_form_cliente()
        self.refrescar_todo()
        messagebox.showinfo("CasaDeCambio",
                            f"Cliente registrado: {cliente.codigo}")

    def _limpiar_form_cliente(self) -> None:
        for clave in ("nombre", "documento", "telefono", "email"):
            self._lc[clave].delete(0, tk.END)

    def _buscar_clientes_gui(self) -> None:
        self._pintar_clientes(self._s.buscar_clientes(self._ent_buscar.get()))

    def _pintar_clientes(self, clientes: List[Cliente]) -> None:
        self._tabla_clientes.delete(*self._tabla_clientes.get_children())
        for c in clientes:
            self._tabla_clientes.insert("", tk.END, values=(
                c.codigo, c.nombre, c.documento, c.telefono or "-",
                c.email or "-"))

    # --- Pestana 4 · Historial ---
    def _construir_historial(self) -> None:
        m = self._f_historial

        filtros = tk.Frame(m, bg=COLOR_PANEL)
        filtros.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(filtros, text="Ver:", bg=COLOR_PANEL, fg=COLOR_TEXTO)\
            .pack(side=tk.LEFT)
        self._var_hist = tk.StringVar(value="TODOS")
        self._cmb_hist = ttk.Combobox(filtros, textvariable=self._var_hist,
                                      state="readonly", width=18,
                                      values=("TODOS", "COMPRA", "VENTA"))
        self._cmb_hist.pack(side=tk.LEFT, padx=(6, 10))
        tk.Button(filtros, text="Filtrar",
                  command=self._refrescar_historial).pack(side=tk.LEFT)
        tk.Label(filtros, text=f"   {len(self._s.transacciones)} "
                  "operaciones en total", bg=COLOR_PANEL,
                  fg=COLOR_TEXTO).pack(side=tk.RIGHT)

        contenedor = tk.Frame(m, bg=COLOR_PANEL)
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)
        columnas = ("folio", "fecha", "tipo", "moneda", "monto", "local",
                    "tasa", "cliente")
        self._tabla_hist = ttk.Treeview(contenedor, columns=columnas,
                                        show="headings")
        for col, ancho in (("folio", 170), ("fecha", 150), ("tipo", 90),
                           ("moneda", 70), ("monto", 90), ("local", 90),
                           ("tasa", 80), ("cliente", 180)):
            self._tabla_hist.heading(col, text=col.upper(),
                                     anchor=tk.CENTER)
            self._tabla_hist.column(col, width=ancho, anchor=tk.CENTER)
        self._tabla_hist.tag_configure("COMPRA", foreground=COLOR_VERDE)
        self._tabla_hist.tag_configure("VENTA", foreground=COLOR_ROJO)
        scroll_y = ttk.Scrollbar(contenedor, orient=tk.VERTICAL,
                                 command=self._tabla_hist.yview)
        self._tabla_hist.configure(yscrollcommand=scroll_y.set)
        self._tabla_hist.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _refrescar_historial(self) -> None:
        lista = reversed(self._s.transacciones)
        filtro = self._var_hist.get() if hasattr(self, "_var_hist") else \
            "TODOS"
        self._tabla_hist.delete(*self._tabla_hist.get_children())
        for tx in lista:
            if filtro != "TODOS" and tx.tipo != filtro:
                continue
            valores = (tx.folio, f"{tx.fecha:%Y-%m-%d %H:%M}", tx.tipo,
                       tx.moneda, f"{tx.monto_divisa:,.2f}",
                       f"{tx.monto_local:,.2f}", f"{tx.tasa:.4f}",
                       tx.cliente)
            self._tabla_hist.insert("", tk.END, tags=(tx.tipo,),
                                    values=valores)

    # --- Pestana 5 · Caja ---
    def _construir_caja(self) -> None:
        m = self._f_caja
        encabezado = tk.Frame(m, bg=COLOR_PANEL)
        encabezado.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(encabezado, text="Cierre de caja (arqueo del día)",
                 bg=COLOR_PANEL, fg=COLOR_DORADO,
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        tk.Button(encabezado, text="Guardar reporte",
                  command=self._guardar_arqueo_gui)\
            .pack(side=tk.RIGHT, padx=8)
        tk.Button(encabezado, text="Generar arqueo",
                  command=self._refrescar_caja).pack(side=tk.RIGHT)

        contenedor = tk.Frame(m, bg="#0e223c")
        contenedor.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        self._txt_caja = tk.Text(contenedor, bg="#0e223c", fg=COLOR_VERDE,
                                 font=FUENTE_MONO, relief=tk.FLAT,
                                 padx=14, pady=12)
        self._txt_caja.pack(fill=tk.BOTH, expand=True)
        self._txt_caja.insert(tk.END, "Genera el arqueo para ver el "
                                      "resumen del día.\n")
        self._txt_caja.config(state=tk.DISABLED)

    def _refrescar_caja(self) -> None:
        try:
            arqueo = self._s.generar_arqueo()
        except Exception:
            return
        self._txt_caja.config(state=tk.NORMAL)
        self._txt_caja.delete("1.0", tk.END)
        self._txt_caja.insert(tk.END, arqueo.texto())
        self._txt_caja.config(state=tk.DISABLED)

    def _guardar_arqueo_gui(self) -> None:
        try:
            ruta = self._s.guardar_arqueo()
        except Exception as err:
            messagebox.showerror("CasaDeCambio", str(err))
            return
        messagebox.showinfo("CasaDeCambio", f"Reporte guardado en:\n{ruta}")

    # --- Refrescos globales ---
    def _seleccion_tabla(self, tabla: ttk.Treeview) -> dict:
        sel = tabla.selection()
        if not sel:
            return {}
        valores = tabla.item(sel[0])["values"]
        return {col: valores[i] for i, col in enumerate(tabla["columns"])}

    def _refrescar_tasas(self) -> None:
        self._tabla_tasas.delete(*self._tabla_tasas.get_children())
        for moneda in self._s.monedas:
            spread = moneda.venta - moneda.compra
            etiqueta = "base" if moneda.es_base else ""
            self._tabla_tasas.insert("", tk.END, tags=(etiqueta,), values=(
                moneda.codigo, moneda.nombre, moneda.simbolo,
                f"{moneda.compra:.4f}", f"{moneda.venta:.4f}",
                f"{spread:.4f}"))

    def _refrescar_combos(self) -> None:
        self._monedas = self._s.monedas
        self._clientes = self._s.clientes
        opciones_moneda = [f"{m.codigo} · {m.nombre}" for m in self._monedas
                           if not m.es_base]
        self._cmb_operar_moneda["values"] = opciones_moneda
        if opciones_moneda and not self._cmb_operar_moneda.get():
            self._cmb_operar_moneda.current(0)

        opciones_cliente = ["PÚBLICO (sin cliente)"] + [
            f"{c.codigo} · {c.nombre}" for c in self._clientes]
        self._cmb_operar_cliente["values"] = opciones_cliente
        if opciones_cliente and not self._cmb_operar_cliente.get():
            self._cmb_operar_cliente.current(0)
        self._pintar_tasa_operar()

    def refrescar_todo(self) -> None:
        self._refrescar_tasas()
        self._pintar_clientes(self._s.clientes)
        self._refrescar_historial()
        self._refrescar_caja()
        self._refrescar_combos()

    def iniciar(self) -> None:
        self._raiz.mainloop()


# ======================================================================
# PUNTO DE ENTRADA
# ======================================================================
def _arreglar_consola() -> None:
    """Evita errores de codificación de acentos en consolas Windows."""
    for flujo in (sys.stdout, sys.stderr):
        reconfigure = getattr(flujo, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> None:
    _arreglar_consola()
    servicio = AppService()

    if len(sys.argv) > 1 and sys.argv[1].strip().lower() in ("cli", "--cli"):
        MenuCLI(servicio).ejecutar()
        return

    app = CasaDeCambioApp(servicio)
    app.iniciar()


if __name__ == "__main__":
    main()