# -*- coding: utf-8 -*-
"""Excepciones de dominio de CasaDeCambio.

Todas las reglas de negocio rotas elevan alguna de estas excepciones
para que la capa de servicios o la interfaz las traduzcan bien.
"""


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