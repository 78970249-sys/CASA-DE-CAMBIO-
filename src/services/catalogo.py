# -*- coding: utf-8 -*-
"""Catálogo inicial de divisas de CasaDeCambio (Célula 1/2).

La moneda base es el dólar (USD), que siempre cotiza 1.0000. Las tasas
de arranque son referenciales; el operador puede ajustarlas desde la
aplicación (compra < venta para dejar margen).
"""

from typing import List

from src.domain.models import Moneda

MONEDAS_INICIALES: List[Moneda] = [
    Moneda("EUR", "Euro", "€", 1.0800, 1.2000),
    Moneda("GBP", "Libra esterlina", "£", 1.2600, 1.4000),
    Moneda("MXN", "Peso mexicano", "$", 0.0480, 0.0580),
    Moneda("CAD", "Dólar canadiense", "C$", 0.7300, 0.8100),
    Moneda("JPY", "Yen japonés", "¥", 0.0063, 0.0074),
]


def monedas_iniciales() -> List[Moneda]:
    """Devuelve la lista inicial (sin USD, que se agrega siempre)."""
    return [
        Moneda("USD", "Dólar estadounidense", "US$", 1.0000, 1.0000),
        *MONEDAS_INICIALES,
    ]