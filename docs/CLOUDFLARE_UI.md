# Cloudflare UI運用ガイド

最終更新: 2026-02-10

## このUIの目的
- 1画面で次の3工程を完了する
1. 候補抽出 (`/v1/trial/live`)
2. 人手レビュー (`/v1/review/queue`, `/v1/review/{id}`)
3. リスク確認 (`/v1/analysis/*`)

## 画面で何をするか

### 1. 候補抽出カード
- 目的: 今日チェックする仕入れ候補を生成する
- 操作:
1. `仕入れ元`, `販売先`, `キーワード`, `カテゴリ` を入力
2. `候補抽出を実行` を押す
3. `auto/human/reject` を確認
4. `再スキャン抑止でスキップ` と `次の検索位置` を確認
5. 先頭から見直したい場合は `先頭から再開` を押す

入力項目の意味:
- `比較件数（日本/eBay同期）`: 日本側とeBay側を同じ件数で取得し、取得分を全件判定
- `商品状態`: `指定なし / 新品のみ / 中古のみ`。新品/中古の不一致ペアは見送り
- `再スキャン抑止時間（分）`: この時間内に「自動採用0件 かつ 要確認0件」だった商品を再スキャンしない
- `カテゴリ候補`: 見出し直下のトグルで選択。カテゴリ欄は1セル展開型（リスト選択）
- `閾値を調整`: 一致度/利益の閾値をUIで変更して、今回抽出に反映

自動調整ルール:
- `source_limit`: Yahoo/楽天とも最大100
- UIでは `market_limit = source_limit` を固定
- UIでは `run_pipeline_top_n = source_limit` を固定（取得した分を全件判定）

重複スキャン抑止:
- スキャン位置は `source_cursor / market_cursor` を自動で前進
- 直近で見込みなしだった商品は `scan_cooldown_minutes` の間スキップ
- API呼び出しを抑えつつ、新しい範囲を優先して進める
- 仕入れ側/eBay側の両方が完了したら、そのキーワードの取得は停止する

推奨の初期値（精度重視）:
- `比較件数（日本/eBay同期）= 8`

### 2. 人手レビューカード
- 目的: 誤判定を落として、仕入れ判断に使う候補だけ残す
- 操作:
1. `Reviewer名` を設定
2. `仕入れページへ` / `eBayページへ` を開いて同一商品か確認
3. `比較` を押して、左右の直リンクを新規タブで確認
4. 行ごとに `承認` または `却下`
5. 必要ならメモを残す

補足:
- `案件ID #xx` はレビュー対象の内部ID
- 比較パネルは埋め込みプレビューを使わず、商品ページの新規タブ確認のみ
- テスト由来データ（mock / cursor系ID）は通常キューに出さない

### 3. リスク分析カード
- 目的: 何がボトルネックか把握して設定改善する
- 操作:
1. `reject理由` 上位を確認
2. `compliance理由` 上位を確認
3. 閾値とクエリを調整して再実行

補足:
- `見送り理由` / `規約注意` は検索条件単位の累積（組み合わせ判定ベース）
- 候補抽出カードの `組み合わせ判定（累積）` と同じ集計軸
- `今回の判定結果` は商品単位
- `累積内訳` で、検索条件ごとの累積 `仕入れ件数 / 販売参照件数 / 判定済み商品数` を確認できる
- 旧データで取得件数が未記録な場合は、`旧データで取得件数が未記録` と表示
- `次の検索位置` は `仕入れ側` / `販売側` を分けて表示し、両方完了時は `全範囲を確認済み` を表示

### 4. API使用率カード
- 目的: API上限を使い切る前に配分を調整する
- 操作:
1. `使用率を更新` を押す
2. Yahoo / 楽天 / eBay の使用率ゲージを確認
3. 高いプロバイダがあれば `source_limit`（= `market_limit`）を下げる

補足:
- ここでの値は「APIリクエスト回数」
- eBayは公式Rate Limits APIから取得できる場合、公式残量を表示
- Yahoo/楽天はローカル抑止設定ベース（公式残量APIではない）
- eBayは「観測回数(直近60分)」と「公式上限窓」が別軸で表示される
- 1リクエストで複数商品を取得できるAPIは、取得件数が増えても回数が+1のことがある
- 詳細説明はカード見出しの `?` マウスオーバーで確認

## ローカル起動

前提: FastAPIが `http://127.0.0.1:8000` で起動済み

```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/cloudflare-ui
npm install
npx wrangler dev --local --port 8788 --var BACKEND_BASE_URL:http://127.0.0.1:8000
```

ブラウザで `http://127.0.0.1:8788` を開く。

## デプロイ

1. Cloudflare認証
```bash
cd /Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/cloudflare-ui
npx wrangler whoami
# 未認証なら
npx wrangler login
```

2. デプロイ
```bash
npx wrangler deploy --var BACKEND_BASE_URL:https://YOUR-BACKEND-URL
```

注意:
- `BACKEND_BASE_URL` は Cloudflare から到達できる公開URLが必要
- `http://127.0.0.1:8000` はデプロイWorkerからは到達できない

## APIプロキシ対応一覧
- `POST /api/trial/live` -> `POST /v1/trial/live`
- `POST /api/trial/reset-state` -> `POST /v1/trial/reset-state`
- `GET /api/review/queue` -> `GET /v1/review/queue`
- `POST /api/review/{id}` -> `POST /v1/review/{id}`
- `GET /api/analysis/reject-reasons` -> `GET /v1/analysis/reject-reasons`
- `GET /api/analysis/compliance-risks` -> `GET /v1/analysis/compliance-risks`
- `GET /api/analysis/api-usage` -> `GET /v1/analysis/api-usage`
- `GET /api/categories/suggestions` -> `GET /v1/categories/suggestions`

## つまずきやすい点
- `BACKEND_BASE_URL is not configured`: 変数未設定
- `Backend fetch failed`: バックエンドURLが外部公開されていない/疎通不可
- `Address already in use`: `--port 8788` など別ポートで起動
- レビュー待ちが0件: 抽出条件が厳しすぎるか、既にレビュー済み
