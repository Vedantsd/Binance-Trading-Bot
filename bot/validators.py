from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

MAX_QUANTITY = Decimal("1_000_000")
MAX_PRICE = Decimal("10_000_000")


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must not be empty.")
    if not symbol.isalnum():
        raise ValueError(f"Symbol '{symbol}' must be alphanumeric (e.g. BTCUSDT).")
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )
    return order_type


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive, got {qty}.")
    if qty > MAX_QUANTITY:
        raise ValueError(f"Quantity {qty} exceeds maximum allowed ({MAX_QUANTITY}).")
    return qty


def validate_price(price: Optional[str | float | Decimal], order_type: str) -> Optional[Decimal]:
    if order_type in ("LIMIT", "STOP_LIMIT"):
        if price is None:
            raise ValueError(f"Price is required for {order_type} orders.")
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be positive, got {p}.")
        if p > MAX_PRICE:
            raise ValueError(f"Price {p} exceeds maximum allowed ({MAX_PRICE}).")
        return p
    if price is not None:
        raise ValueError("Price should not be provided for MARKET orders.")
    return None


def validate_stop_price(stop_price: Optional[str | float | Decimal], order_type: str) -> Optional[Decimal]:
    if order_type == "STOP_LIMIT":
        if stop_price is None:
            raise ValueError("Stop price (--stop-price) is required for STOP_LIMIT orders.")
        try:
            sp = Decimal(str(stop_price))
        except InvalidOperation:
            raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
        if sp <= 0:
            raise ValueError(f"Stop price must be positive, got {sp}.")
        return sp
    return None


def validate_all(symbol: str, side: str, order_type: str, quantity: str | float | Decimal, price: Optional[str | float | Decimal] = None, stop_price: Optional[str | float | Decimal] = None) -> dict:
    params: dict = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type.strip().upper()),
        "stop_price": validate_stop_price(stop_price, order_type.strip().upper()),
    }
    return params