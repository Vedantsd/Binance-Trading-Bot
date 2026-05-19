from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient
from bot.logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    time_in_force: Optional[str] = None
    client_order_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    @classmethod
    def from_api_response(cls, data: dict) -> "OrderResult":
        avg = data.get("avgPrice") or data.get("price") or "N/A"
        return cls(
            success=True,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("type"),
            status=data.get("status"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=avg,
            price=data.get("price"),
            time_in_force=data.get("timeInForce"),
            client_order_id=data.get("clientOrderId"),
            raw=data,
        )

    @classmethod
    def from_error(cls, message: str) -> "OrderResult":
        return cls(success=False, error_message=message)

    def summary_lines(self) -> list[str]:
        if not self.success:
            return [f"  ✗ Error: {self.error_message}"]
        lines = [
            f"  Order ID       : {self.order_id}",
            f"  Symbol         : {self.symbol}",
            f"  Side           : {self.side}",
            f"  Type           : {self.order_type}",
            f"  Status         : {self.status}",
            f"  Orig Qty       : {self.orig_qty}",
            f"  Executed Qty   : {self.executed_qty}",
            f"  Avg Price      : {self.avg_price}",
        ]
        if self.time_in_force:
            lines.append(f"  Time-In-Force  : {self.time_in_force}")
        return lines





def _build_api_params(symbol: str, side: str, order_type: str, quantity: Decimal, price: Optional[Decimal] = None, stop_price: Optional[Decimal] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": str(quantity),
    }

    if order_type == "LIMIT":
        if price is None:
            raise ValueError("Price required for LIMIT order.")
        params["price"] = str(price)
        params["timeInForce"] = "GTC"

    elif order_type == "STOP_LIMIT":
        if price is None or stop_price is None:
            raise ValueError("Both price and stop_price required for STOP_LIMIT order.")
        params["type"] = "STOP"
        params["price"] = str(price)
        params["stopPrice"] = str(stop_price)
        params["timeInForce"] = "GTC"

    return params


def place_order(client: BinanceFuturesClient, symbol: str, side: str, order_type: str, quantity: Decimal, price: Optional[Decimal] = None, stop_price: Optional[Decimal] = None ) -> OrderResult:
    logger.info(
        "place_order called: symbol=%s side=%s type=%s qty=%s price=%s stop_price=%s",
        symbol, side, order_type, quantity, price, stop_price,
    )

    try:
        api_params = _build_api_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
        response = client.place_order(**api_params)
        result = OrderResult.from_api_response(response)
        logger.info(
            "Order result: orderId=%s status=%s executedQty=%s avgPrice=%s",
            result.order_id, result.status, result.executed_qty, result.avg_price,
        )
        return result

    except Exception as exc:
        logger.error("Order failed: %s", exc, exc_info=True)
        return OrderResult.from_error(str(exc))


def place_market_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: Decimal) -> OrderResult:
    return place_order(client, symbol, side, "MARKET", quantity)


def place_limit_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: Decimal, price: Decimal) -> OrderResult:
    return place_order(client, symbol, side, "LIMIT", quantity, price=price)


def place_stop_limit_order(client: BinanceFuturesClient, symbol: str, side: str, quantity: Decimal, price: Decimal, stop_price: Decimal) -> OrderResult:
    return place_order(client, symbol, side, "STOP_LIMIT", quantity, price=price, stop_price=stop_price)