# -*- coding: utf-8 -*-
"""Persistencia de CasaDeCambio en archivos JSON.

Cada colección vive en un archivo dentro de la carpeta ``data/``:

+------------------+---------------------------+
| Archivo          | Colección                 |
+------------------+---------------------------+
| monedas.json     | catálogo de divisas       |
| clientes.json    | clientes registrados      |
| transacciones.json | historial de operaciones |
+------------------+---------------------------+

Los tickets y arqueos también pueden guardarse como texto plano en
``data/Tickets/`` y ``data/Reportes/``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Union

from src.domain.models import Cliente, Moneda, Transaccion
from src.services.catalogo import monedas_iniciales

Ruta = Union[str, Path]


def _default_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


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

    # ------------------------------------------------------------------
    # Monedas
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Transacciones
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Tickets y reportes
    # ------------------------------------------------------------------
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