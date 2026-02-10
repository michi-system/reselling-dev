# 運用手順

最終更新: 2026-02-10

## 日次運用フロー
1. 新規仕入れ商品を登録
2. 市場候補を登録
3. `/v1/pipeline/run` 実行
4. `/v1/analysis/reject-reasons` でreject主因を確認
5. `human_review` を `/review` または `/v1/review/*` で確定
6. 採用/不採用の学習データ化 (次フェーズ)

## GUI日次運用フロー (推奨)
1. Cloudflare UIを開く
2. 「候補抽出」で `query/category` を入力して実行
   - カテゴリは候補トグル/検索セレクトから選択可（手入力も可）
3. 「人手レビュー」で `承認/却下` を確定
4. 「リスク分析」で reject/compliance理由を確認
5. 必要に応じて閾値と検索語を調整して再実行

参照: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/docs/CLOUDFLARE_UI.md`

補足:
- `scan_cooldown_minutes` の間は、前回「自動採用0かつ要確認0」だった商品を再スキャンしない
- スキャン位置は `source_cursor/market_cursor` で進むため、同じ範囲の重複取得を抑制
- API使用量は `GET /v1/analysis/api-usage` で直近1時間の使用率を確認できる
- スプレッドシート連携はCSV出力を利用:
  - `GET /v1/export/opportunities.csv`
  - `GET /v1/export/reviews.csv`
  - `GET /v1/export/api-usage.csv`

## 共有URL更新フロー（自分用）
ローカルDBを使ったまま、Cloudflare UIからアクセスできる共有URLを更新する。

```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev
bash scripts/deploy_share_ui.sh
```

実行内容:
1. backend再起動
2. `cloudflared` で backend 一時公開（`trycloudflare`）
3. `BACKEND_BASE_URL` を更新して Cloudflare Worker 再デプロイ

停止:
```bash
bash scripts/stop_share_backend.sh
```

注意:
- `trycloudflare` URL は一時URL（再実行ごとに変わる場合あり）
- `cloudflared` 停止で公開backendは利用不可

## 実API試用フロー
1. `.env` に `YAHOO_CLIENT_ID / RAKUTEN_APP_ID / (必要時 RAKUTEN_ACCESS_KEY) / EBAY_CLIENT_ID / EBAY_CLIENT_SECRET` を設定
2. `/v1/trial/live` を実行
3. 取込件数が0の場合は `query` を変更して再実行
4. `source_runs` の `auto_accept` と `human_review` を確認

補足:
- eBay未承認時は `market_source=mock` で仕入れ側フローだけ先行検証可能
- `scripts/check_live_connectivity.py` で接続可否を先に確認すると切り分けが早い
- `COMPLIANCE_MODE=strict` では一部 `auto_accept` が `human_review` に降格される
- Yahoo/Rakuten/eBayは内部スロットリングでQPSを抑制（`*_MIN_INTERVAL_SECONDS`）
- `AUTO_ACCEPT_REQUIRES_TRUSTED_PRICE=true` では `price_confidence=trusted` 以外を自動採用しない
- 収益閾値は `MIN_EXPECTED_PROFIT_JPY`、利幅閾値は `MIN_EXPECTED_MARGIN_RATE` / `CATEGORY_MIN_MARGIN_OVERRIDES` で調整する

## コンプライアンス運用
1. `COMPLIANCE_MODE=warn` で開始して、実データのリスク傾向を確認
2. `GET /v1/analysis/compliance-risks` で理由分布を確認
3. 本番運用は `COMPLIANCE_MODE=strict` を検討

## 人手レビュー運用
1. Queue取得: `GET /v1/review/queue`
2. 承認/却下: `POST /v1/review/{opportunity_id}`
3. 既レビュー案件はQueueから除外される

## 定期実行運用
1. ジョブ作成: `POST /v1/batch/jobs`
2. 即時確認: `POST /v1/batch/jobs/{job_id}/run`
3. 履歴確認: `GET /v1/batch/runs`
4. 常駐中はスケジューラが `next_run_at` 到達ジョブを自動実行

## 監視すべき指標
- 自動採用率
- 人手確認率
- 誤採用率
- 平均利益率
- API使用率（Yahoo/楽天/eBay）

## 運用ルール
- 閾値変更前後でサンプル比較を行う
- 誤判定が出たら `decision_trace` から原因特定
- いきなり全体変更せず、段階ロールアウト

## 学習機能の現状
- 現在はルールベース判定（`decision_trace` 保存あり）で、機械学習モデルの自動再学習は未実装
- 人手レビュー結果はDBに蓄積されるため、次フェーズで学習データとして利用可能

## 障害時の確認順
1. `/health`
2. DB接続
3. 入力データ品質 (JAN/型番欠落)
4. ルール閾値設定
