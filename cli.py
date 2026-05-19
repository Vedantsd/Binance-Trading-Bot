from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

from dotenv import load_dotenv

from bot.client import APIError, AuthenticationError, BinanceFuturesClient, NetworkError
from bot.logging_config import get_logger, setup_logging
from bot.orders import place_order
from bot.validators import validate_all


load_dotenv()
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
log = get_logger("cli")


_SEPARATOR = "─" * 60


def _print_section(title: str) -> None:
    print(f"\n{_SEPARATOR}")
    print(f"  {title}")
    print(_SEPARATOR)


def _make_client() -> BinanceFuturesClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com").strip()

    if not api_key or not api_secret:
        print(
            "\n[ERROR] BINANCE_API_KEY and BINANCE_API_SECRET must be set.\n"
            "        Export them as environment variables or place them in a .env file."
        )
        sys.exit(1)

    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret, base_url=base_url)


def cmd_place(args: argparse.Namespace) -> None:
    try:
        params = validate_all(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n[VALIDATION ERROR] {exc}")
        log.warning("Validation failed: %s", exc)
        sys.exit(1)

    _print_section("ORDER REQUEST SUMMARY")
    print(f"  Symbol         : {params['symbol']}")
    print(f"  Side           : {params['side']}")
    print(f"  Type           : {params['order_type']}")
    print(f"  Quantity       : {params['quantity']}")
    if params["price"] is not None:
        print(f"  Price          : {params['price']}")
    if params["stop_price"] is not None:
        print(f"  Stop Price     : {params['stop_price']}")
    print(_SEPARATOR)

    log.info(
        "Submitting order: %s %s %s qty=%s price=%s stop=%s",
        params["side"], params["order_type"], params["symbol"],
        params["quantity"], params["price"], params["stop_price"],
    )

    client = _make_client()
    result = place_order(
        client=client,
        symbol=params["symbol"],
        side=params["side"],
        order_type=params["order_type"],
        quantity=params["quantity"],
        price=params["price"],
        stop_price=params["stop_price"],
    )

    _print_section("ORDER RESPONSE")
    for line in result.summary_lines():
        print(line)
    print(_SEPARATOR)

    if result.success:
        print(f"\nOrder placed successfully!\n")
        log.info("CLI: order placed successfully (orderId=%s)", result.order_id)
    else:
        print(f"\nOrder failed.\n")
        log.error("CLI: order failed — %s", result.error_message)
        sys.exit(1)


def cmd_open_orders(args: argparse.Namespace) -> None:
    client = _make_client()
    symbol = args.symbol.strip().upper() if args.symbol else None

    try:
        orders = client.get_open_orders(symbol=symbol)
    except (APIError, NetworkError) as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)

    _print_section(f"OPEN ORDERS{' — ' + symbol if symbol else ''}")
    if not orders:
        print("  No open orders found.")
    else:
        for o in orders:
            print(
                f"  orderId={o['orderId']}  {o['side']} {o['type']}  "
                f"qty={o['origQty']}  price={o.get('price','N/A')}  "
                f"status={o['status']}"
            )
    print(_SEPARATOR + "\n")


def cmd_account(args: argparse.Namespace) -> None:
    client = _make_client()

    try:
        info = client.get_account_info()
    except (APIError, NetworkError) as exc:
        print(f"\n[ERROR] {exc}")
        sys.exit(1)

    _print_section("ACCOUNT INFO")
    print(f"  Can Trade      : {info.get('canTrade')}")
    print(f"  Total Wallet   : {info.get('totalWalletBalance')} USDT")
    print(f"  Unrealised PnL : {info.get('totalUnrealizedProfit')} USDT")
    print(f"  Available Bal  : {info.get('availableBalance')} USDT")
    print(_SEPARATOR + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO).",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    place_p = sub.add_parser("place", help="Place a new futures order.")
    place_p.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT.")
    place_p.add_argument(
        "--side", required=True, choices=["BUY", "SELL"], help="Order side."
    )
    place_p.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        help="Order type.",
    )
    place_p.add_argument("--qty", required=True, type=str, help="Order quantity.")
    place_p.add_argument(
        "--price",
        default=None,
        type=str,
        help="Limit price (required for LIMIT / STOP_LIMIT).",
    )
    place_p.add_argument(
        "--stop-price",
        dest="stop_price",
        default=None,
        type=str,
        help="Trigger price (required for STOP_LIMIT).",
    )
    place_p.set_defaults(func=cmd_place)

    oo_p = sub.add_parser("open-orders", help="List open orders.")
    oo_p.add_argument("--symbol", default=None, help="Filter by symbol.")
    oo_p.set_defaults(func=cmd_open_orders)

    acc_p = sub.add_parser("account", help="Show account balance summary.")
    acc_p.set_defaults(func=cmd_account)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)

    try:
        args.func(args)
    except AuthenticationError as exc:
        print(f"\n[AUTH ERROR] {exc}")
        log.error("Authentication error: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)


if __name__ == "__main__":
    main()