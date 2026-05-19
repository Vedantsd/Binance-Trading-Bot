from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("client")


class TradingBotError(Exception):
    """Base exception for all trading-bot errors."""


class APIError(TradingBotError):
    """Raised when Binance returns a non-2xx response or an error JSON body."""

    def __init__(self, code: int, message: str, raw: Optional[dict] = None):
        self.code = code
        self.message = message
        self.raw = raw or {}
        super().__init__(f"[{code}] {message}")


class NetworkError(TradingBotError):
    """Raised on connection failures."""


class AuthenticationError(TradingBotError):
    """Raised when API key / secret are missing"""


class BinanceFuturesClient:
    DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
    _RECV_WINDOW = 5000  

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise AuthenticationError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        self._time_offset: int = 0  
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)


    def _sync_time(self) -> None:
        try:
            resp = self._session.get(
                f"{self.base_url}/fapi/v1/time", timeout=self.timeout
            )
            server_time: int = resp.json()["serverTime"]
            self._time_offset = server_time - int(time.time() * 1000)
            logger.debug("Time offset synced: %d ms", self._time_offset)
        except Exception as exc:
            logger.warning("Could not sync server time: %s", exc)

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params


    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False,) -> dict:
        if signed:
            if self._time_offset == 0:
                self._sync_time()
            params = params or {}
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self._RECV_WINDOW
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug("→ %s %s  params=%s", method.upper(), endpoint, params)

        try:
            response = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() == "POST" else None,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise NetworkError(f"Request timed out after {self.timeout}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"Connection error: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Unexpected network error: {exc}") from exc

        logger.debug(
            "← HTTP %d  body=%s",
            response.status_code,
            response.text[:500],
        )

        try:
            data: dict = response.json()
        except ValueError:
            data = {"raw": response.text}

        if not response.ok:
            code = data.get("code", response.status_code)
            msg = data.get("msg", response.reason or "Unknown error")
            logger.error("API error [%s]: %s | full=%s", code, msg, data)
            raise APIError(code=int(code), message=msg, raw=data)

        return data


    def get_server_time(self) -> dict:
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self) -> dict:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account_info(self) -> dict:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **order_params) -> dict:
        logger.info(
            "Placing order: %s",
            {k: v for k, v in order_params.items() if k != "signature"},
        )
        result = self._request("POST", "/fapi/v1/order", params=order_params, signed=True)
        logger.info("Order placed successfully: orderId=%s", result.get("orderId"))
        return result

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order: symbol=%s orderId=%s", symbol, order_id)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)