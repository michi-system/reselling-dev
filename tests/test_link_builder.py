from app.api import routes
from app.db.models import MarketItem, SourceItem


def test_build_market_link_from_browse_item_id() -> None:
    market = MarketItem(
        marketplace="ebay",
        market_item_id="ebay:v1|123456789012|0",
        category="audio",
        title="Sony speaker",
        brand="Sony",
        model_number="",
        gtin="",
        condition="new",
        price_usd=100.0,
        shipping_usd=0.0,
        price_confidence="semi_trusted",
    )
    link = routes._build_market_link(market)
    assert link == "https://www.ebay.com/itm/123456789012"


def test_build_source_link_for_mock_source_uses_search() -> None:
    source = SourceItem(
        source_site="mock-source",
        source_item_id="mock-source:src-001",
        category="audio",
        title="sony speaker main unit",
        brand="Sony",
        model_number="",
        jan="",
        condition="new",
        price_jpy=1000.0,
        shipping_jpy=0.0,
        weight_g=100,
    )
    link = routes._build_source_link(source)
    assert link.startswith("https://shopping.yahoo.co.jp/search?p=")


def test_build_source_link_for_rakuten_item_code_uses_direct_item_page() -> None:
    source = SourceItem(
        source_site="rakuten-ichiba",
        source_item_id="rakuten-ichiba:shop-name:item-001",
        category="audio",
        title="sony speaker",
        brand="Sony",
        model_number="",
        jan="",
        condition="new",
        price_jpy=1000.0,
        shipping_jpy=0.0,
        weight_g=100,
    )
    link = routes._build_source_link(source)
    assert link == "https://item.rakuten.co.jp/shop-name/item-001/"


def test_build_source_link_for_prefixed_url_keeps_direct_url() -> None:
    source = SourceItem(
        source_site="rakuten-ichiba",
        source_item_id="rakuten-ichiba:https://item.rakuten.co.jp/shop/item-001/",
        category="audio",
        title="sony speaker",
        brand="Sony",
        model_number="",
        jan="",
        condition="new",
        price_jpy=1000.0,
        shipping_jpy=0.0,
        weight_g=100,
    )
    link = routes._build_source_link(source)
    assert link == "https://item.rakuten.co.jp/shop/item-001/"
