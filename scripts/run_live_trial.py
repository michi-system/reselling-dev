from __future__ import annotations

import argparse
import json

from app.adapters.ebay import EbayBrowseAdapter
from app.adapters.errors import ExternalApiError
from app.adapters.mock import MockMarketAdapter
from app.adapters.rakuten import RakutenIchibaAdapter
from app.adapters.yahoo import YahooShoppingAdapter
from app.db.session import SessionLocal, init_db
from app.services.trial import run_live_trial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live trial using source API + eBay Browse API")
    parser.add_argument("--source-site", choices=["yahoo", "rakuten"], required=True)
    parser.add_argument("--market-source", choices=["ebay", "mock"], default="ebay")
    parser.add_argument("--query", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--source-limit", type=int, default=5)
    parser.add_argument("--market-limit", type=int, default=40)
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--item-condition", choices=["any", "new", "used"], default="any")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    init_db()

    source_adapter = YahooShoppingAdapter() if args.source_site == "yahoo" else RakutenIchibaAdapter()
    market_adapter = EbayBrowseAdapter() if args.market_source == "ebay" else MockMarketAdapter()

    db = SessionLocal()
    try:
        result = run_live_trial(
            db=db,
            source_adapter=source_adapter,
            market_adapter=market_adapter,
            source_site=args.source_site,
            market_source=args.market_source,
            query=args.query,
            category=args.category,
            source_limit=args.source_limit,
            market_limit=args.market_limit,
            run_pipeline_top_n=args.top_n,
            only_small_items=False,
            listing_condition_filter=args.item_condition,
        )
    except ExternalApiError as exc:
        db.close()
        print(f"Live trial failed: {exc}")
        return 1

    db.close()
    print(json.dumps(
        {
            "query": result.query,
            "category": result.category,
            "source_site": result.source_site,
            "market_source": args.market_source,
            "imported_source_items": result.imported_source_items,
            "imported_market_items": result.imported_market_items,
            "processed_source_items": result.processed_source_items,
            "skipped_recent_source_items": result.skipped_recent_source_items,
            "source_cursor": result.source_cursor,
            "market_cursor": result.market_cursor,
            "scan_cooldown_minutes": result.scan_cooldown_minutes,
            "source_runs": [r.__dict__ for r in result.results],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
