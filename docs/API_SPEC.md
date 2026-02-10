# API仕様 (MVP)

最終更新: 2026-02-10

## GET /health
- 用途: ヘルスチェック
- 応答: `{ "status": "ok" }`

## POST /v1/source-items
- 用途: 仕入れ商品の登録
- 必須: `source_site`, `source_item_id`, `category`, `title`, `price_jpy`

## GET /v1/source-items
- 用途: 仕入れ商品の一覧

## POST /v1/market-items
- 用途: 販売候補商品の登録
- 必須: `market_item_id`, `category`, `title`, `price_usd`

## GET /v1/market-items
- 用途: 販売候補商品の一覧

## POST /v1/pipeline/run
- 用途: 判定パイプライン実行
- 入力: `source_item_id`, `category(任意)`, `only_small_items`
- 出力: 判定件数サマリと機会一覧

## GET /v1/opportunities
- 用途: 判定結果一覧
- クエリ: `decision`, `limit`

## GET /v1/analysis/reject-reasons
- 用途: rejectの主要原因集計
- クエリ: `limit` (最大5000)
- 出力: `total_rejects`, `reasons[{reason,count}]`

## GET /v1/analysis/compliance-risks
- 用途: 規約/運用ガードレールに関するリスク理由の集計
- クエリ: `limit` (最大5000)
- 出力: `total_flagged`, `reasons[{reason,count}]`

## GET /v1/analysis/api-usage
- 用途: このアプリ内での各API呼び出し状況（直近1時間）を確認
- 出力:
  - `window_minutes`
  - `items[{provider,calls_last_hour,hourly_budget,usage_rate_percent,remaining_calls,usage_basis,limit_window,note}]`

補足:
- `eBay` は可能な場合、公式 `Rate Limits API` の残量を使用
- `Yahoo/楽天` は直近呼び出し回数とローカル抑止設定ベース（公式残量APIは未使用）

## GET /v1/system/fx-rate
- 用途: 利益計算に使う現在のUSD/JPYレート状態を確認
- 出力:
  - `pair` (`USDJPY`)
  - `rate`
  - `source`
  - `fetched_at`
  - `next_refresh_at`
  - `last_error`
  - `auto_update_enabled`

## POST /v1/system/fx-rate/refresh
- 用途: USD/JPYレートを即時更新（手動）
- 出力: `GET /v1/system/fx-rate` と同形式

## GET /v1/system/thresholds
- 用途: 判定に使う既定閾値を取得（UI初期表示用）
- クエリ:
  - `category` (任意: 指定時はカテゴリ別最低利益率の解決値を返す)
- 出力:
  - `min_auto_accept_score`
  - `min_human_review_score`
  - `min_title_similarity_auto_accept`
  - `min_title_similarity_human_review`
  - `min_expected_profit_jpy`
  - `min_expected_margin_rate`
  - `accessory_reject_score`

## GET /v1/categories/suggestions
- 用途: 仕入れ元/販売先に合わせたカテゴリ候補を取得（トグル・検索セレクト用）
- クエリ:
  - `source_site`
  - `market_source`
  - `query` (検索キーワード)
  - `selected_category` (現在入力中カテゴリ)
  - `q` (候補検索文字列)
  - `limit`
- 出力:
  - `total`
  - `items[{key,internal_category,label_ja,source_hint,market_hint,aliases,score}]`

## GET /v1/export/opportunities.csv
- 用途: 判定結果をCSVでエクスポート（スプレッドシート取込用）
- クエリ: `limit` (最大10000)

## GET /v1/export/reviews.csv
- 用途: 人手レビュー結果をCSVでエクスポート（スプレッドシート取込用）
- クエリ: `limit` (最大10000)

## GET /v1/export/api-usage.csv
- 用途: API使用率集計をCSVでエクスポート（スプレッドシート取込用）

## GET /v1/review/queue
- 用途: `human_review` で未確定の案件一覧
- クエリ: `limit`, `include_mock` (既定: false)
- 主な返却:
  - `source_title`, `market_title`
  - `source_site`, `source_item_external_id`, `source_link`
  - `source_category`, `source_condition`, `source_price_jpy`, `source_shipping_jpy`
  - `market_site`, `market_item_external_id`, `market_link`
  - `market_category`, `market_condition`, `market_price_usd`, `market_shipping_usd`, `market_revenue_jpy`
  - `match_score`, `expected_profit_jpy`, `expected_margin_rate`
  - `decision_trace`

## POST /v1/review/{opportunity_id}
- 用途: 人手レビュー確定
- 入力: `outcome(approve/reject)`, `reviewer`, `note`

## GET /review
- 用途: 人手レビュー簡易UI
- 補足: APIを直接叩く代わりにブラウザから承認/却下できる

## POST /v1/trial/live
- 用途: 実APIを使って試用実行（仕入れ候補取得 + eBay候補取得 + 判定）
- 入力:
  - `source_site`: `yahoo` または `rakuten`
  - `market_source`: `ebay` または `mock`
  - `query`: 検索キーワード
  - `category`: 内部カテゴリ文字列（例: `audio`）
  - `item_condition`: `any` / `new` / `used`（新品/中古フィルタ）
  - `thresholds` (任意):
    - `min_auto_accept_score`
    - `min_human_review_score`
    - `min_expected_profit_jpy`
    - `min_expected_margin_rate`
    - `min_title_similarity_auto_accept`
    - `min_title_similarity_human_review`
    - `accessory_reject_score`
  - `source_limit`: 仕入れ側の取得件数
  - `market_limit`: eBay側の取得件数（`/v1/trial/live` では `source_limit` と同値に正規化）
  - `run_pipeline_top_n`: 判定対象にする仕入れ件数（実行時は `source_limit` と同値に正規化）
  - `scan_cooldown_minutes`: 再スキャン抑止時間（分）
- 出力:
  - 取込件数（source/market）
  - 判定処理件数（商品単位）
  - スキップ件数（最近スキャン済み・見込みなし）
  - 次回カーソル（source/market）
  - sourceごとの `auto_accept/human_review/reject` 件数
  - `run_total_rejects` / `run_total_compliance_flagged` は商品単位の件数
  - `source_cursor = -1` の場合は仕入れ側が全範囲完了（この場合は販売側のみの取得は行わず終了）

## POST /v1/trial/reset-state
- 用途: 現在の検索条件の検索位置を先頭に戻す
- 入力:
  - `source_site`
  - `market_source`
  - `query`
  - `category`
  - `item_condition` (`any` / `new` / `used`)
- 出力:
  - `source_cursor`（0へ初期化）
  - `market_cursor`（0へ初期化）

## GET /v1/trial/summary
- 用途: 検索条件（仕入れ元/販売先/キーワード/カテゴリ）単位の累積サマリ
- 補足: 集計は日次でリセット（既定タイムゾーン: `Asia/Tokyo`）
- クエリ:
  - `source_site`
  - `market_source`
  - `query`
  - `category`
  - `item_condition` (`any` / `new` / `used`)
- 出力:
  - `total_runs`
  - `total_source_items_processed`
  - `total_source_items_imported`
  - `total_market_items_imported`
  - `pair_auto_accept_total`, `pair_human_review_total`, `pair_reject_total`
  - `pair_total`
  - `reject_reasons[{reason,count}]`
  - `compliance_reasons[{reason,count}]`
  - `last_run_at`

補足:
- 大きすぎる件数入力は実行時に自動調整される
  - `source_limit`: Yahoo/ Rakutenとも最大100
  - `market_limit`: `source_limit` と同値（日本/eBayの取得件数を同期）
  - `run_pipeline_top_n`: `source_limit` と同値（取得分を全件判定）

## POST /v1/batch/jobs
- 用途: 定期実行ジョブ作成
- 入力:
  - `name`, `enabled`
  - `source_site`, `market_source`
  - `query`, `category`
  - `source_limit`, `market_limit`, `run_pipeline_top_n`
  - `only_small_items`, `interval_minutes`

## GET /v1/batch/jobs
- 用途: バッチジョブ一覧

## POST /v1/batch/jobs/{job_id}/run
- 用途: ジョブを即時手動実行

## GET /v1/batch/runs
- 用途: 実行履歴確認
- クエリ: `job_id`, `limit`
