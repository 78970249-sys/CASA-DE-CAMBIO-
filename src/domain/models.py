# -*- coding: utf-8 -*-
"""Modelo de dominio de CasaDeCambio.

Entidades puras del negocio de una casa de cambio profesional:

- :class:`Moneda`: divisa con tasas de compra y venta (cotización).
- :class:`Cliente`: persona que opera en la casa.
- :class:`Transaccion`: operación de compra/venta de divisa con su ticket.
- :class:`CierreCaja` y :class:`MovimientosMoneda`: arqueo diario.

La moneda **base** es el dólar estadounidense (``USD``): las otras
divisas se cotizan en dólares por unidad. La casa **compra** divisa al
tipo de compra (paga dólares) y la **vende** al tipo de venta (recibe
dólares); la diferencia (spread) es su utilidad.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import FrozenSet, List

from .exceptions import (
    ClienteDuplicadoError,
    ClienteInvalidoError,
    MonedaInvalidaError,
    TasaInvalidaError,
    TransaccionInvalidaError,
)

__all__ = [
    "CODIGO_BASE",
    "CierreCaja",
    "Cliente",
    "Moneda",
    "MovimientosMoneda",
    "SIN_CLIENTE",
    "Transaccion",
    "TIPOS_OPERACION",
]

CODIGO_BASE: str = "USD"
"""Código de la moneda local (dólar estadounidense)."""

SIN_CLIENTE: str = "PÚBLICO (sin cliente)"
"""Etiqueta usada cuando una operación no se registra a nombre de nadie."""

TIPOS_OPERACION: FrozenSet[str] = frozenset({"COMPRA", "VENTA"})
"""Operaciones permitidas: la casa compra divisa o la casa vende divisa."""


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