from app.db.models import MarketItem, SourceItem
from app.db.session import SessionLocal, init_db


def main() -> None:
    init_db()
    db = SessionLocal()

    if db.query(SourceItem).count() > 0 or db.query(MarketItem).count() > 0:
        print("Skip seed: data already exists.")
        db.close()
        return

    source = SourceItem(
        source_site="yahoo-shopping",
        source_item_id="ys-1001",
        category="audio",
        title="Sony ABC-100 Bluetooth Speaker New",
        brand="Sony",
        model_number="ABC-100",
        jan="4900000000001",
        condition="new",
        price_jpy=8800,
        shipping_jpy=600,
        weight_g=460,
    )
    db.add(source)

    market_good = MarketItem(
        marketplace="ebay",
        market_item_id="eb-2001",
        category="audio",
        title="Sony ABC-100 Bluetooth Speaker New in Box",
        brand="Sony",
        model_number="ABC-100",
        gtin="4900000000001",
        condition="new",
        price_usd=189,
        shipping_usd=18,
        price_confidence="trusted",
    )

    market_bad = MarketItem(
        marketplace="ebay",
        market_item_id="eb-2002",
        category="audio",
        title="Speaker Case Cover for Sony ABC-100",
        brand="",
        model_number="",
        gtin="",
        condition="new",
        price_usd=11,
        shipping_usd=4,
        price_confidence="semi_trusted",
    )

    db.add_all([market_good, market_bad])
    db.commit()
    db.close()
    print("Seed completed.")


if __name__ == "__main__":
    main()
