"""Conversion de moneda a MXN, segun el ADR-002.

USD se convierte a MXN con el tipo de cambio fijo de 18.5 que fija el
ADR-002; MXN pasa sin cambio. El valor y la moneda originales se
conservan siempre junto con el valor convertido, para que cualquier
estimacion se pueda rastrear hasta su origen.
"""

from __future__ import annotations

from typing import NamedTuple

USD_TO_MXN_RATE = 18.5
_SUPPORTED_CURRENCIES = frozenset({"USD", "MXN"})


class ConvertedAmount(NamedTuple):
    """Resultado de convertir un monto a MXN, con el original intacto."""

    mxn: float
    original_amount: float
    original_currency: str


def to_mxn(amount: float, currency: str) -> ConvertedAmount:
    """Convierte `amount` de `currency` a MXN segun el tipo de cambio del ADR-002.

    Lanza `ValueError` para cualquier moneda distinta de USD o MXN,
    porque el ADR-002 solo contempla esas dos en este dataset.
    """
    if currency not in _SUPPORTED_CURRENCIES:
        raise ValueError(f"moneda no soportada para conversion a MXN: {currency!r}")

    rate = USD_TO_MXN_RATE if currency == "USD" else 1.0
    mxn = round(float(amount) * rate, 2)
    return ConvertedAmount(mxn=mxn, original_amount=amount, original_currency=currency)
