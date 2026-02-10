from __future__ import annotations

import argparse

from app.adapters.ebay import EbayBrowseAdapter
from app.adapters.errors import ExternalApiError
from app.adapters.rakuten import RakutenIchibaAdapter
from app.adapters.yahoo import YahooShoppingAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check live API connectivity")
    parser.add_argument("--query", default="sony")
    parser.add_argument("--category", default="audio")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    checks = [
        ("yahoo", lambda: YahooShoppingAdapter().fetch(query=args.query, category=args.category, limit=1)),
        ("rakuten", lambda: RakutenIchibaAdapter().fetch(query=args.query, category=args.category, limit=1)),
        ("ebay", lambda: EbayBrowseAdapter().fetch(query=args.query, category=args.category, limit=1)),
    ]

    all_ok = True
    for name, fn in checks:
        try:
            records = fn()
            print(f"[{name}] OK: fetched {len(records)} record(s)")
        except ExternalApiError as exc:
            all_ok = False
            print(f"[{name}] ERROR: {exc}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
