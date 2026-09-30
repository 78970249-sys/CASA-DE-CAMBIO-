# -*- coding: utf-8 -*-
"""Pruebas del dominio de CasaDeCambio (Célula 1)."""

import unittest

from src.domain.exceptions import (
    ClienteInvalidoError,
    MonedaInvalidaError,
    TasaInvalidaError,
    TransaccionInvalidaError,
)
from src.domain.models import (
    Cliente,
    Moneda,
    Transaccion,
    generar_ticket,
)


class PruebaMoneda(unittest.TestCase):
    def test_moneda_valida_con_spread(self):
        m = Moneda("EUR", "Euro", "€", 1.08, 1.20)
        self.assertEqual("EUR", m.codigo)
        self.assertEqual(1.08, m.compra)
        self.assertEqual(1.20, m.venta)
        self.assertFalse(m.es_base)

    def test_codigo_de_tres_letras(self):
        with self.assertRaises(MonedaInvalidaError):
            Moneda("EU", "Euro", "€", 1.08, 1.20)

    def test_tasas_negativas_rechazadas(self):
        with self.assertRaises(TasaInvalidaError):
            Moneda("GBP", "Libra", "£", 1.26, -1.0)

    def test_spread_invalido_rechazado(self):
        with self.assertRaises(TasaInvalidaError):
            Moneda("MXN", "Peso mexicano", "$", 0.06, 0.05)

    def test_usd_siempre_a_uno(self):
        with self.assertRaises(TasaInvalidaError):
            Moneda("USD", "Dólar", "US$", 1.02, 1.08)
        m = Moneda("USD", "Dólar", "US$", 1.0, 1.0)
        self.assertTrue(m.es_base)


class PruebaCliente(unittest.TestCase):
    def test_cliente_obligatorio(self):
        with self.assertRaises(ClienteInvalidoError):
            Cliente("CLI-0001", "", "04872342-1")

    def test_cliente_sin_documento_rechazado(self):
        with self.assertRaises(ClienteInvalidoError):
            Cliente("CLI-0001", "Ana López", "")


class PruebaTicket(unittest.TestCase):
    def _tx(self, tipo="COMPRA"):
        return Transaccion(
            folio="TX-20260929-0001",
            fecha=__import__("datetime").datetime.now(),
            tipo=tipo,
            moneda="EUR",
            moneda_nombre="Euro",
            simbolo="€",
            tasa=1.08,
            monto_divisa=100,
            monto_local=108.0,
            cliente="Ana López",
        )

    def test_ticket_compra(self):
        ticket = generar_ticket(self._tx("COMPRA"))
        self.assertIn("FOLIO:", ticket.upper())
        self.assertIn("TX-20260929-0001", ticket.upper())
        self.assertIn("COMPRA DE DIVISA", ticket)
        self.assertIn("100.00 EUR", ticket)

    def test_ticket_venta(self):
        ticket = generar_ticket(self._tx("VENTA"))
        self.assertIn("VENTA DE DIVISA", ticket)
        self.assertIn("108.00", ticket)

    def test_tipo_invalido(self):
        with self.assertRaises(TransaccionInvalidaError):
            self._tx("PESOS")


if __name__ == "__main__":
    unittest.main()