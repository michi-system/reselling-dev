# Reselling Opportunity Engine (MVP)

日本仕入れ品と海外EC販売候補を比較し、最低限使える形で利益機会を抽出するためのバックエンドです。

## このMVPのゴール
- 最低限動く: 仕入れ商品と販売候補を登録し、判定パイプラインを実行できる
- 修正しやすい: ルールをモジュール分割し、判定理由(`decision_trace`)を保存する
- 拡張しやすい: APIアダプタ・モデル置き換えを前提にした構造

## 技術スタック
- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite (初期)
- pytest

## セットアップ
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

`.env` に以下を設定してください（値は貼らない）:
- `YAHOO_CLIENT_ID`
- `RAKUTEN_APP_ID`
- `RAKUTEN_ACCESS_KEY` (必要な場合)
- `EBAY_CLIENT_ID`
- `EBAY_CLIENT_SECRET`
- `EBAY_MARKETPLACE_ID` (`EBAY_US` 推奨)
- `COMPLIANCE_MODE` (`warn/strict/off`)
- `AUTO_ACCEPT_REQUIRES_TRUSTED_PRICE` (`true/false`)
- `MIN_EXPECTED_MARGIN_RATE` (例: `0.10`)
- `CATEGORY_MIN_MARGIN_OVERRIDES` (例: `audio:0.12,camera:0.15`)
- `MIN_EXPECTED_PROFIT_JPY` (例: `500`)
- `MIN_AUTO_ACCEPT_SCORE` (例: `0.85`)
- `MIN_HUMAN_REVIEW_SCORE` (例: `0.40`)
- `FX_AUTO_UPDATE_ENABLED` (`true/false`)
- `FX_UPDATE_INTERVAL_MINUTES` (例: `60`)
- `FX_RATE_PROVIDER_URL` (例: `https://open.er-api.com/v6/latest/USD`)
- `SCAN_SUMMARY_RESET_TIMEZONE` (例: `Asia/Tokyo`)
- `API_USAGE_USE_EBAY_RATE_API` (`true/false`)
- `EBAY_RATE_LIMIT_API_URL` (既定: `https://api.ebay.com/developer/analytics/v1_beta/rate_limit/`)

注記: 楽天Ichibaは新OpenAPIエンドポイントを使用します（legacy endpoint廃止対応）。

## 起動
```bash
uvicorn app.main:app --reload
```

- APIドキュメント: `http://127.0.0.1:8000/docs`
- ヘルスチェック: `GET /health`

## ローカル再起動（バックエンド+UI）
```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev
bash scripts/restart_local.sh
```

個別再起動:
```bash
bash scripts/restart_local.sh backend
bash scripts/restart_local.sh ui
```

## 共有用ワンコマンド（自分用）
ローカルDBをそのまま使いながら、Cloudflare UIからアクセス可能な共有URLを更新します。

```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev
bash scripts/deploy_share_ui.sh
```

実行内容:
1. backend再起動
2. `cloudflared` で backend を一時公開（`trycloudflare`）
3. `BACKEND_BASE_URL` をその公開URLにして Cloudflare Worker を再デプロイ

停止:
```bash
bash scripts/stop_share_backend.sh
```

注意:
- `trycloudflare` URL は一時URLです。再実行ごとに変わる可能性があります。
- `cloudflared` を止めると公開backendは使えなくなります。

## サンプルデータ投入
```bash
python scripts/seed_sample_data.py
```

## API最短動作確認
```bash
curl -X POST http://127.0.0.1:8000/v1/source-items -H 'Content-Type: application/json' -d @sample_data/source_item_audio.json
curl -X POST http://127.0.0.1:8000/v1/market-items -H 'Content-Type: application/json' -d @sample_data/market_item_good.json
curl -X POST http://127.0.0.1:8000/v1/market-items -H 'Content-Type: application/json' -d @sample_data/market_item_accessory.json
curl -X POST http://127.0.0.1:8000/v1/pipeline/run -H 'Content-Type: application/json' -d '{"source_item_id":1,"only_small_items":true}'
```

## 実APIライブ試用（source API + eBay）
サーバー起動後:
```bash
curl -X POST http://127.0.0.1:8000/v1/trial/live \
  -H 'Content-Type: application/json' \
  -d '{"source_site":"yahoo","market_source":"ebay","query":"sony speaker","category":"audio","item_condition":"new","source_limit":3,"market_limit":20,"run_pipeline_top_n":2,"scan_cooldown_minutes":60}'
```

CLIで直接実行する場合:
```bash
python scripts/run_live_trial.py --source-site yahoo --market-source ebay --query "sony speaker" --category audio --item-condition new --source-limit 3 --market-limit 20 --top-n 2
```

eBay審査待ち中に試用だけ先に進める場合:
```bash
python scripts/run_live_trial.py --source-site yahoo --market-source mock --query "sony speaker" --category audio --item-condition new --source-limit 3 --market-limit 2 --top-n 2
```

接続チェック:
```bash
python scripts/check_live_connectivity.py --query sony --category audio
```

補足:
- `source_limit` はYahoo/楽天とも最大100へ実行時に自動調整
- カテゴリ候補は `GET /v1/categories/suggestions` で取得可能（Cloudflare UIのトグル選択で使用）
- 仕入れ側/eBay側の両方が完了したキーワードは、次回以降の取得を停止

## 精度分析
rejectの主因を確認:
```bash
curl 'http://127.0.0.1:8000/v1/analysis/reject-reasons?limit=1000'
```

規約リスクの集計を確認:
```bash
curl 'http://127.0.0.1:8000/v1/analysis/compliance-risks?limit=1000'
```

API使用率（直近1時間）を確認:
```bash
curl 'http://127.0.0.1:8000/v1/analysis/api-usage'
```

為替レート状態（USD/JPY）を確認:
```bash
curl 'http://127.0.0.1:8000/v1/system/fx-rate'
```

為替レートを即時更新:
```bash
curl -X POST 'http://127.0.0.1:8000/v1/system/fx-rate/refresh'
```

補足:
- Yahoo/楽天のAPI使用率は、直近呼び出し回数 + ローカル抑止設定ベース
- eBayは可能な場合、公式Rate Limits APIの残量を優先表示
- 1リクエストで複数件を返すAPIでは、取得件数と増加回数は一致しません
- 為替(USD/JPY)は `FX_RATE_PROVIDER_URL` から定期更新され、利益計算に自動反映されます

スプレッドシート取込用CSVを出力:
```bash
curl -o opportunities.csv 'http://127.0.0.1:8000/v1/export/opportunities.csv?limit=5000'
curl -o reviews.csv 'http://127.0.0.1:8000/v1/export/reviews.csv?limit=5000'
curl -o api_usage.csv 'http://127.0.0.1:8000/v1/export/api-usage.csv'
```

## 人手レビュー
- Queue API: `GET /v1/review/queue`
- 確定API: `POST /v1/review/{opportunity_id}`
- 簡易UI: [http://127.0.0.1:8000/review](http://127.0.0.1:8000/review)

## Cloudflare Worker GUI
1画面で「候補抽出 -> レビュー -> 分析」を回す運用UIです。
- 比較は埋め込みプレビューではなく、商品ページ直リンクを新規タブで確認する方式です（危険表示対策）。
- 判定閾値（一致度/利益）をUIから調整して実行できます。

ローカル起動:
```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/cloudflare-ui
npm install
npx wrangler dev --local --port 8788 --var BACKEND_BASE_URL:http://127.0.0.1:8000
```

デプロイ:
```bash
npx wrangler deploy --var BACKEND_BASE_URL:https://YOUR-BACKEND-URL
```

詳細: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/docs/CLOUDFLARE_UI.md`

## 定期実行（バッチ）
ジョブ作成:
```bash
curl -X POST http://127.0.0.1:8000/v1/batch/jobs \
  -H 'Content-Type: application/json' \
  -d '{"name":"daily-audio","enabled":true,"source_site":"yahoo","market_source":"ebay","query":"sony speaker","category":"audio","source_limit":3,"market_limit":20,"run_pipeline_top_n":2,"only_small_items":true,"interval_minutes":1440}'
```

手動実行:
```bash
curl -X POST http://127.0.0.1:8000/v1/batch/jobs/1/run
```

履歴確認:
```bash
curl 'http://127.0.0.1:8000/v1/batch/runs?job_id=1&limit=20'
```

## テスト
```bash
.venv/bin/pytest -q
```

## ディレクトリ
- `app/api`: FastAPIルート
- `app/services`: 判定ロジック
- `app/db`: DBモデル/セッション
- `app/adapters`: 外部取得アダプタの抽象層
- `docs`: 日本語ドキュメント

## ドキュメント
- `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/docs/INDEX.md`

## 重要方針
- ルールや閾値を変えたら、`rule_version`と`docs`を同時更新する
- 判断不能な候補は`human_review`に倒し、誤採用を避ける
- 利益計算は保守的に行い、楽観バイアスを入れない
- ドキュメント更新ポリシーは `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/docs/DOC_POLICY.md` を参照
- 現在の判定はルールベースであり、レビュー結果の自動学習は次フェーズ実装
