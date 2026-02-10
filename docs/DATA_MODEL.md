# データモデル

最終更新: 2026-02-10

## source_items
- 仕入れ商品マスター
- 主キー: `id`
- 一意制約: `source_item_id`
- 主な属性: `category`, `title`, `brand`, `model_number`, `jan`, `condition`, `price_jpy`, `weight_g`

## market_items
- 販売市場候補
- 主キー: `id`
- 一意制約: `market_item_id`
- 主な属性: `category`, `title`, `brand`, `model_number`, `gtin`, `condition`, `price_usd`, `price_confidence`

## opportunities
- 比較結果
- 主キー: `id`
- 外部キー: `source_item_id`, `market_item_id`
- 主な属性: `match_score`, `accessory_score`, `decision`, `decision_trace`, `expected_profit_jpy`, `expected_margin_rate`, `rule_version`

## review_decisions
- 人手レビュー確定結果
- 主キー: `id`
- 一意制約: `opportunity_id` (1案件1確定)
- 主な属性: `outcome`, `reviewer`, `note`, `created_at`

## batch_jobs
- 定期実行ジョブ設定
- 主キー: `id`
- 一意制約: `name`
- 主な属性:
  - 入力条件: `source_site`, `market_source`, `query`, `category`
  - 取得件数: `source_limit`, `market_limit`, `run_pipeline_top_n`
  - 実行条件: `enabled`, `only_small_items`, `interval_minutes`
  - スケジュール: `last_run_at`, `next_run_at`

## batch_runs
- ジョブ実行履歴
- 主キー: `id`
- 外部キー: `job_id`
- 主な属性: `status`, `message`, `summary_json`, `started_at`, `finished_at`

## scan_states
- スキャン位置（カーソル）管理
- 主キー: `id`
- 一意制約: `source_site + market_source + query + category`
- 主な属性: `source_cursor`, `market_cursor`, `updated_at`
- 用途:
  - 重複スキャンを減らす
  - 次回実行時に前回の続きから取得する

## source_scan_histories
- ソース商品の直近スキャン結果管理
- 主キー: `id`
- 一意制約: `source_item_id + source_site + query + category`
- 主な属性: `scanned_at`, `auto_accept_count`, `human_review_count`, `reject_count`
- 用途:
  - `scan_cooldown_minutes` の間、見込みなし商品の再スキャンを抑止
  - スキップ件数をUIに表示

## api_usage_events
- API呼び出しイベントログ（使用率集計用）
- 主キー: `id`
- 主な属性: `provider`, `called_at`
- 用途:
  - 直近1時間のAPI使用率集計
  - プロセス再起動後もカウント維持（`--reload`対策）

## 設計上の注意
- ログ追跡のため `decision_trace` はJSON文字列で保持
- ルール変更時に追跡できるよう `rule_version` を保持
- `review_decisions` と `batch_runs` で運用履歴を永続化
- `scan_states` と `source_scan_histories` でAPI節約と重複スキャン抑止を実現
