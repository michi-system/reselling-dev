from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryPreset:
    key: str
    internal_category: str
    label_ja: str
    source_hints: dict[str, str]
    market_hints: dict[str, str]
    aliases: tuple[str, ...]


CATEGORY_PRESETS: tuple[CategoryPreset, ...] = (
    CategoryPreset(
        key="audio_speaker",
        internal_category="audio",
        label_ja="オーディオ・スピーカー",
        source_hints={
            "yahoo": "家電 > オーディオ機器 > スピーカー",
            "rakuten": "TV・オーディオ・カメラ > オーディオ > スピーカー",
        },
        market_hints={"ebay": "Consumer Electronics > Portable Audio & Headphones"},
        aliases=("speaker", "スピーカー", "bluetooth speaker", "soundbar", "オーディオ"),
    ),
    CategoryPreset(
        key="camera_lens",
        internal_category="camera",
        label_ja="カメラ・レンズ",
        source_hints={
            "yahoo": "家電 > カメラ > 交換レンズ",
            "rakuten": "TV・オーディオ・カメラ > カメラ > 交換レンズ",
        },
        market_hints={"ebay": "Cameras & Photo > Lenses & Filters"},
        aliases=("camera", "レンズ", "lens", "canon", "nikon", "sony alpha"),
    ),
    CategoryPreset(
        key="game_console",
        internal_category="game",
        label_ja="ゲーム本体・周辺機器",
        source_hints={
            "yahoo": "ゲーム、おもちゃ > テレビゲーム",
            "rakuten": "テレビゲーム > 本体・周辺機器",
        },
        market_hints={"ebay": "Video Games & Consoles"},
        aliases=("game", "ゲーム", "switch", "ps5", "xbox", "controller"),
    ),
    CategoryPreset(
        key="pc_parts",
        internal_category="pc",
        label_ja="PCパーツ",
        source_hints={
            "yahoo": "スマホ、タブレット、パソコン > PCパーツ",
            "rakuten": "パソコン・周辺機器 > PCパーツ",
        },
        market_hints={"ebay": "Computers/Tablets & Networking > Computer Components"},
        aliases=("gpu", "cpu", "pc", "ssd", "memory", "グラボ", "マザーボード"),
    ),
    CategoryPreset(
        key="smartphone",
        internal_category="smartphone",
        label_ja="スマートフォン",
        source_hints={
            "yahoo": "スマホ、タブレット、パソコン > スマホ本体",
            "rakuten": "スマートフォン・タブレット > スマートフォン本体",
        },
        market_hints={"ebay": "Cell Phones & Smartphones"},
        aliases=("iphone", "android", "smartphone", "スマホ", "galaxy", "pixel"),
    ),
    CategoryPreset(
        key="watch",
        internal_category="watch",
        label_ja="腕時計",
        source_hints={
            "yahoo": "ファッション > 腕時計",
            "rakuten": "腕時計",
        },
        market_hints={"ebay": "Jewelry & Watches > Watches"},
        aliases=("watch", "腕時計", "g-shock", "seiko", "citizen", "casio"),
    ),
    CategoryPreset(
        key="toy_figure",
        internal_category="toy",
        label_ja="ホビー・フィギュア",
        source_hints={
            "yahoo": "ゲーム、おもちゃ > フィギュア",
            "rakuten": "ホビー > コレクション",
        },
        market_hints={"ebay": "Toys & Hobbies > Action Figures"},
        aliases=("figure", "フィギュア", "プラモデル", "model kit", "pokemon", "ホビー"),
    ),
    CategoryPreset(
        key="beauty",
        internal_category="beauty",
        label_ja="美容家電・コスメ",
        source_hints={
            "yahoo": "コスメ、美容、ヘアケア",
            "rakuten": "美容・コスメ・香水",
        },
        market_hints={"ebay": "Health & Beauty"},
        aliases=("美容", "コスメ", "beauty", "skincare", "dryer", "ヘアアイロン"),
    ),
    CategoryPreset(
        key="home_appliance",
        internal_category="home",
        label_ja="生活家電",
        source_hints={
            "yahoo": "家電 > 生活家電",
            "rakuten": "家電 > 生活家電",
        },
        market_hints={"ebay": "Home & Garden > Household Appliances"},
        aliases=("掃除機", "vacuum", "炊飯器", "kitchen", "home appliance"),
    ),
    CategoryPreset(
        key="tool",
        internal_category="tool",
        label_ja="電動工具",
        source_hints={
            "yahoo": "DIY、工具 > 電動工具",
            "rakuten": "花・ガーデン・DIY > DIY・工具",
        },
        market_hints={"ebay": "Home & Garden > Tools"},
        aliases=("工具", "tool", "インパクト", "drill", "makita", "hikoki"),
    ),
)


@dataclass(frozen=True)
class CategorySuggestion:
    key: str
    internal_category: str
    label_ja: str
    source_hint: str
    market_hint: str
    aliases: tuple[str, ...]
    score: float


def suggest_categories(
    source_site: str,
    market_source: str,
    query_text: str = "",
    selected_category: str = "",
    search_text: str = "",
    limit: int = 30,
) -> list[CategorySuggestion]:
    normalized_source = (source_site or "").strip().lower()
    normalized_market = (market_source or "").strip().lower()
    normalized_selected = (selected_category or "").strip().lower()
    normalized_query = (query_text or "").strip().lower()
    normalized_search = (search_text or "").strip().lower()

    items: list[CategorySuggestion] = []
    for preset in CATEGORY_PRESETS:
        source_hint = preset.source_hints.get(normalized_source, "")
        market_hint = preset.market_hints.get(normalized_market, "")
        searchable_parts = [
            preset.internal_category.lower(),
            preset.label_ja.lower(),
            source_hint.lower(),
            market_hint.lower(),
            " ".join(alias.lower() for alias in preset.aliases),
        ]
        searchable_blob = " ".join(part for part in searchable_parts if part)
        if normalized_search and normalized_search not in searchable_blob:
            continue

        score = _score_preset(
            preset=preset,
            normalized_query=normalized_query,
            normalized_selected=normalized_selected,
        )
        items.append(
            CategorySuggestion(
                key=preset.key,
                internal_category=preset.internal_category,
                label_ja=preset.label_ja,
                source_hint=source_hint,
                market_hint=market_hint,
                aliases=preset.aliases,
                score=score,
            )
        )

    items.sort(key=lambda item: (-item.score, item.label_ja))
    return items[: max(1, min(int(limit), 200))]


def _score_preset(preset: CategoryPreset, normalized_query: str, normalized_selected: str) -> float:
    score = 0.0
    if normalized_selected and normalized_selected == preset.internal_category.lower():
        score += 3.0

    if normalized_query:
        if preset.internal_category.lower() in normalized_query:
            score += 2.0
        if preset.label_ja.lower() in normalized_query:
            score += 2.0
        for alias in preset.aliases:
            if alias.lower() in normalized_query:
                score += 1.5
    return score
