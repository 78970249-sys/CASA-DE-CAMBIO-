# -*- coding: utf-8 -*-
"""Fachada de casos de uso de CasaDeCambio (Célula 2 · Servicios).

Es el único punto de acceso que conoce la interfaz (Célula 3):

- Cotización y edición de tasas (compra/venta).
- Clientes: alta y búsqueda por nombre/código/documento.
- Operaciones: comprar y vender divisa contra USD.
- Tickets: texto imprimible y archivo por folio.
- Cierre de caja: arqueo diario por divisa.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import List, Optional, Union

from src.domain.exceptions import (
    ClienteDuplicadoError,
    ClienteInvalidoError,
    ClienteNoEncontradoError,
    MonedaNoEncontradaError,
    MonedaInvalidaError,
    TransaccionInvalidaError,
)
from src.domain.models import (
    CierreCaja,
    Cliente,
    CODIGO_BASE,
    Moneda,
    MovimientosMoneda,
    SIN_CLIENTE,
    Transaccion,
    generar_ticket,
)
from src.services.data_manager import CasaDataManager

_NUM = r"^\d+(\.\d{1,2})?$"


class AppService:
    """Orquesta dominio + datos y expone los casos de uso de la casa."""

    def __init__(self, ruta_datos: Optional[str] = None) -> None:
        self._data = CasaDataManager(ruta_datos)
        self._monedas: List[Moneda] = self._data.cargar_monedas()
        self._clientes: List[Cliente] = self._data.cargar_clientes()
        self._transacciones: List[Transaccion] = self._data.cargar_transacciones()

    # ------------------------------------------------------------------
    # Acceso a colecciones (copias de seguridad)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Tasas y monedas
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
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

    def obtener_cliente_por_documento(self, documento: str) -> Optional[Cliente]:
        busqueda = documento.strip().upper()
        return next(
            (c for c in self._clientes if c.documento.upper() == busqueda),
            None,
        )

    # ------------------------------------------------------------------
    # Operaciones de compra/venta
    # ------------------------------------------------------------------
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
            raise TransaccionInvalidaError(
                "El monto debe ser un número."
            )
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

    # ------------------------------------------------------------------
    # Tickets y cierre de caja
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Utilidades de entrada
    # ------------------------------------------------------------------
    @staticmethod
    def validar_monto(texto: str) -> float:
        """Valida y convierte un monto escrito por el usuario (uso UI/CLI).

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