# -*- coding: utf-8 -*-
"""Interfaz de consola de CasaDeCambio (Célula 3).

Menú paso a paso que consume únicamente la fachada :class:`AppService`.
Es la entrega formal del enunciado; la GUI (tkinter) es la presentación
de demostración.
"""

from __future__ import annotations

from typing import List, Optional

from src.domain.models import Cliente, Moneda, Transaccion
from src.services.app_service import AppService


class MenuCLI:
    """Menú interactivo de consola para el operador de la casa."""

    def __init__(self, servicio: AppService) -> None:
        self._s = servicio

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Consulta cotizaciones
    # ------------------------------------------------------------------
    def _cotizaciones(self) -> None:
        print("\n=== COTIZACIONES DE HOY (US$ por unidad) ===")
        print(f"{'Divisa':<7} {'Nombre':<22} {'Compra':>9} {'Venta':>9}")
        for m in self._s.monedas:
            print(f"{m.codigo:<7} {m.nombre:<22} {m.compra:>8.4f} "
                  f"{m.venta:>8.4f}")

    # ------------------------------------------------------------------
    # Operación
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Actualizar tasas
    # ------------------------------------------------------------------
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
        if input(f"¿Eliminar '{codigo}'? (sí/no): ").lower() != "sí" and \
                input(f"Confirma eliminación de {codigo} (escribe si): ")\
                != "si":
            print("Cancelado.")
            return
        try:
            moneda = self._s.eliminar_moneda(codigo)
        except Exception as err:
            print(f"\nError: {err}")
        else:
            print(f"Moneda eliminada: {moneda.codigo}")

    # ------------------------------------------------------------------
    # Clientes
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Historial y cierre de caja
    # ------------------------------------------------------------------
    def _historial(self, transacciones: Optional[List[Transaccion]] = None) -> None:
        lista = transacciones if transacciones is not None \
            else reversed(self._s.transacciones)
        lista = list(lista)
        if not lista:
            print("\nAún no hay operaciones registradas.")
            return
        print("\n=== HISTORIAL DE OPERACIONES ===")
        print(f"{'Folio':<18} {'Fecha':<17} {'Tipo':<7} {'Divisa':<7} "
              f"{'Monto':>10} {'US$':>10} {'Cliente':<10}")
        for t in lista:
            print(f"{t.folio:<18} {t.fecha:%Y-%m-%d %H:%M:<9} {t.tipo:<7} "
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

    # ------------------------------------------------------------------
    # Utilidades de entrada
    # ------------------------------------------------------------------
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
        documento = input("Documento del cliente (vacío = buscar por nombre): ")\
            .strip()
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