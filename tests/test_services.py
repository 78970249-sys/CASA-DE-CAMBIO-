# -*- coding: utf-8 -*-
"""Pruebas del servicio (casos de uso) de CasaDeCambio (Célula 2)."""

import os
import shutil
import tempfile
import unittest
from datetime import date

from src.domain.exceptions import (
    ClienteDuplicadoError,
    MonedaNoEncontradaError,
    TransaccionInvalidaError,
)
from src.services.app_service import AppService


class PruebaServicioBase(unittest.TestCase):
    """Cada prueba opera sobre un directorio temporal aislado."""

    def setUp(self):
        self._carpeta = tempfile.mkdtemp(prefix="casa_test_")
        self.s = AppService(self._carpeta)

    def tearDown(self):
        shutil.rmtree(self._carpeta, ignore_errors=True)


class PruebaCatalogoMonedas(PruebaServicioBase):
    def test_seis_monedas_con_usd(self):
        monedas = self.s.monedas
        self.assertEqual(6, len(monedas))
        self.assertEqual("USD", monedas[0].codigo)
        self.assertTrue(monedas[0].es_base)

    def test_obtener_moneda_por_codigo(self):
        m = self.s.obtener_moneda("eur")
        self.assertEqual("EUR", m.codigo)

    def test_moneda_no_encontrada(self):
        with self.assertRaises(MonedaNoEncontradaError):
            self.s.obtener_moneda("XXX")

    def test_actualizar_tasa_pide_spread(self):
        with self.assertRaises(Exception):
            self.s.actualizar_tasa("EUR", 1.20, 1.10)


class PruebaOperaciones(PruebaServicioBase):
    def test_comprar_divisa(self):
        tx = self.s.comprar("EUR", 150.00)
        euro = self.s.obtener_moneda("EUR")
        self.assertEqual("COMPRA", tx.tipo)
        self.assertEqual(150.00, tx.monto_divisa)
        self.assertEqual(round(150 * euro.compra, 2), tx.monto_local)
        self.assertTrue(tx.folio.startswith("TX-"))
        self.assertEqual(1, len(self.s.transacciones))

    def test_ticket_se_genera(self):
        tx = self.s.comprar("MXN", 500)
        ticket = self.s.ticket(tx)
        self.assertIn(tx.folio, ticket)
        self.assertIn("US$", ticket)

    def test_vender_usa_tasa_venta(self):
        tx = self.s.vender("GBP", 50)
        libra = self.s.obtener_moneda("GBP")
        self.assertEqual("VENTA", tx.tipo)
        self.assertEqual(round(50 * libra.venta, 2), tx.monto_local)

    def test_usd_no_es_transable(self):
        with self.assertRaises(TransaccionInvalidaError):
            self.s.comprar("USD", 10)

    def test_monto_no_positivo_rechazado(self):
        with self.assertRaises(TransaccionInvalidaError):
            self.s.comprar("EUR", 0)

    def test_folios_secuenciales_en_orden(self):
        a = self.s.comprar("EUR", 10)
        b = self.s.comprar("EUR", 20)
        self.assertLess(a.folio, b.folio)


class PruebaClientes(PruebaServicioBase):
    def test_registrar_y_buscar(self):
        c = self.s.crear_cliente("Ana López", "02478521-4",
                                 "7771-2233", "ana@mail.com")
        self.assertTrue(c.codigo.startswith("CLI-"))
        encontrados = self.s.buscar_clientes("ana")
        self.assertEqual(1, len(encontrados))
        self.assertEqual("02478521-4", encontrados[0].documento)

    def test_documento_duplicado(self):
        self.s.crear_cliente("Ana López", "02478521-4")
        with self.assertRaises(ClienteDuplicadoError):
            self.s.crear_cliente("Otro López", "02478521-4")

    def test_operacion_a_nombre_de_cliente(self):
        cliente = self.s.crear_cliente("Luis Pérez", "99999999-9")
        tx = self.s.comprar("CAD", 80, cliente)
        self.assertEqual("Luis Pérez", tx.cliente)

    def test_operacion_publica(self):
        tx = self.s.comprar("EUR", 10)
        self.assertIn("PÚBLICO", tx.cliente)


class PruebaPersistencia(PruebaServicioBase):
    def test_datos_se_recuperan_al_recargar(self):
        self.s.comprar("EUR", 100)
        self.s.crear_cliente("Ana López", "02478521-4")
        self.s.actualizar_tasa("EUR", 1.10, 1.20)

        recargado = AppService(self._carpeta)
        self.assertEqual(1, len(recargado.transacciones))
        self.assertEqual(1, len(recargado.clientes))
        self.assertEqual(1.10, recargado.obtener_moneda("EUR").compra)


class PruebaArqueo(PruebaServicioBase):
    def test_arqueo_del_dia(self):
        self.s.comprar("EUR", 100)
        self.s.vender("EUR", 40)
        arqueo = self.s.generar_arqueo()
        self.assertEqual(date.today(), arqueo.fecha)
        self.assertEqual(2, arqueo.transacciones)
        euro_caja = next(m for m in arqueo.movimientos
                         if m.codigo == "EUR")
        self.assertEqual(100, euro_caja.compradas)
        self.assertEqual(40, euro_caja.vendidas)
        self.assertEqual(60, euro_caja.posicion)
        moneda = self.s.obtener_moneda("EUR")
        esperado = round(40 * moneda.venta - 100 * moneda.compra, 2)
        self.assertEqual(esperado, arqueo.resultado_del_dia)

    def test_guardar_ticket_y_arqueo(self):
        tx = self.s.comprar("EUR", 100)
        ruta_ticket = self.s.guardar_ticket(tx)
        self.assertTrue(os.path.exists(ruta_ticket))
        ruta_arqueo = self.s.guardar_arqueo()
        self.assertTrue(os.path.exists(ruta_arqueo))
        with open(ruta_ticket, encoding="utf-8") as fh:
            self.assertIn(tx.folio, fh.read())


class PruebaValidacionMonto(PruebaServicioBase):
    def test_monto_valido(self):
        self.assertEqual(150.5, self.s.validar_monto("150,50"))

    def test_monto_invalido(self):
        with self.assertRaises(TransaccionInvalidaError):
            self.s.validar_monto("abc")
        with self.assertRaises(TransaccionInvalidaError):
            self.s.validar_monto("-5")


if __name__ == "__main__":
    unittest.main()