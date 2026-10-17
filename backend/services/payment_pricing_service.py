"""Validated server-side pricing configuration for payment readiness.

Prices are supplied by deployment configuration; this module intentionally
contains no defaults and never reads prices from a client request.
"""

import json
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Mapping

PRICE_CATALOG_ENV = "PAYMENT_PRICES_JSON"
CURRENCY_ENV = "PAYMENT_CURRENCY"
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_MAX_PAYMENT_AMOUNT = Decimal("99999999.99")


def get_server_price_catalog(
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, dict[str, Decimal]]:
    """Return configured currency and positive prices, or an empty catalog.

    Deployment configuration must supply a three-letter currency code and a
    JSON object mapping service names to positive decimal values. No sample
    prices are installed here.
    """
    settings = os.environ if environ is None else environ
    raw_currency = settings.get(CURRENCY_ENV, "").strip()
    raw_catalog = settings.get(PRICE_CATALOG_ENV, "").strip()
    if not raw_currency or not raw_catalog:
        return None, {}

    currency = raw_currency.upper()
    if not _CURRENCY_PATTERN.fullmatch(currency):
        return None, {}

    try:
        parsed = json.loads(raw_catalog)
    except (TypeError, json.JSONDecodeError):
        return None, {}
    if not isinstance(parsed, dict) or not parsed:
        return None, {}

    prices: dict[str, Decimal] = {}
    for service_name, raw_amount in parsed.items():
        if not isinstance(service_name, str) or not service_name.strip():
            return None, {}
        if not isinstance(raw_amount, (str, int, float)) or isinstance(raw_amount, bool):
            return None, {}
        normalized_name = service_name.strip().casefold()
        if normalized_name in prices:
            return None, {}
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, ValueError):
            return None, {}
        if (
            not amount.is_finite()
            or amount <= 0
            or amount > _MAX_PAYMENT_AMOUNT
            or amount.as_tuple().exponent < -2
        ):
            return None, {}
        try:
            prices[normalized_name] = amount.quantize(Decimal("0.01"))
        except InvalidOperation:
            return None, {}

    return currency, prices


def is_server_pricing_configured(
    environ: Mapping[str, str] | None = None,
) -> bool:
    currency, catalog = get_server_price_catalog(environ)
    return currency is not None and bool(catalog)
