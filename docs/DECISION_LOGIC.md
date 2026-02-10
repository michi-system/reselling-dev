# 判定ロジック

最終更新: 2026-02-10

## 1. 一致スコア (`match_score`)
実装: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services/matcher.py`

評価要素:
- JAN/GTIN完全一致
- 型番一致
- ブランド一致
- タイトル類似度 (Jaccard)
- 型番断片欠落ペナルティ
- コンディション一致/不一致ペナルティ

補助指標:
- `title_similarity` を明示算出し、最終判定ゲートで使用

## 2. 付属品リスク (`accessory_score`)
実装: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services/accessory_filter.py`

評価要素:
- 付属品キーワード
- 付属品パターン (`for`, `compatible with`, `replacement` など)
- 型番/ブランドトークン欠落
- コアトークン重なり不足
- 価格の極端下振れ

## 3. 利益計算
実装: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services/profit.py`

計算要素:
- 予想売上 (USD -> JPY)
- eBay手数料 + 決済手数料
- 国際送料推定
- 包装コスト
- 仕入れ原価

## 4. 最終判定
実装: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services/pipeline.py`

ルール:
- `accessory_score >= ACCESSORY_REJECT_SCORE` -> `reject`
- `match_score >= MIN_AUTO_ACCEPT_SCORE`
  かつ `title_similarity >= MIN_TITLE_SIMILARITY_AUTO_ACCEPT`
  かつ `margin >= min_margin_rate(category)`
  かつ `profit >= MIN_EXPECTED_PROFIT_JPY`
  かつ `price_confidence != noisy`
  かつ `AUTO_ACCEPT_REQUIRES_TRUSTED_PRICE=true` の場合は `price_confidence=trusted` -> `auto_accept`
- `match_score >= MIN_HUMAN_REVIEW_SCORE`
  かつ `title_similarity >= MIN_TITLE_SIMILARITY_HUMAN_REVIEW`
  かつ `profit >= MIN_EXPECTED_PROFIT_JPY` -> `human_review`
- それ以外 -> `reject`

`reject` 時は `reject_reason` をトレースに保存。

補足:
- `min_margin_rate(category)` は `CATEGORY_MIN_MARGIN_OVERRIDES` がある場合にカテゴリ別閾値を優先し、未指定カテゴリは `MIN_EXPECTED_MARGIN_RATE` を使う
- 主な `reject_reason`: `accessory_risk_high`, `profit_below_threshold`, `margin_below_threshold`, `title_similarity_low`, `match_score_low`, `price_confidence_low`

## 4.1 コンプライアンスガードレール
実装: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services/compliance.py`

モード:
- `COMPLIANCE_MODE=off`: ガードレール無効
- `COMPLIANCE_MODE=warn`: 判定は維持し、リスク理由のみ記録
- `COMPLIANCE_MODE=strict`: 高リスク条件で `auto_accept` を `human_review` へ降格

代表ルール:
- `cross_market_to_ebay` かつ `BLOCK_AUTO_ACCEPT_CROSS_MARKET=true` の場合、`auto_accept` をブロック
- `mercari_terms_sensitive_source` は `strict` で強制 `human_review`
- コンプライアンス判定は通常ルール適用後に実行し、`auto_accept`/`human_review` を降格させることがある

## 5. トレース保存
- `decision_trace` に理由を保存
- `reject_reason`, `title_similarity`, `expected_margin_rate` を保存
- `compliance_mode`, `compliance_risk_level`, `compliance_reasons` を保存
- ルール変更時は `rule_version` を更新
