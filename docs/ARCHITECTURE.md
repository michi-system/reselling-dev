# アーキテクチャ

最終更新: 2026-02-10

## 方針
- 複雑な処理を1回で完了させない
- 役割ごとにモジュールを分ける
- 仕様変更時は小さい単位で修正できる形を維持

## 構成
1. API層: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/api/routes.py`
2. ドメイン層: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/services`
3. 永続化層: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/db`
4. 外部連携層: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/adapters`
5. 運用UI層 (Cloudflare Worker): `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/cloudflare-ui`

ドメイン層の主要モジュール:
- 判定: `pipeline.py`, `matcher.py`, `accessory_filter.py`, `profit.py`
- 試用: `trial.py`
- 分析: `analytics.py`
- API使用量: `api_usage.py`
- レビュー: `review.py`
- 定期実行: `batch.py`, `scheduler.py`

## 外部連携アダプタ
- Yahoo商品検索: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/adapters/yahoo.py`
- 楽天Ichiba検索: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/adapters/rakuten.py`
- eBay Browse/OAuth: `/Users/tadamichikimura/Downloads/dev-HQ/reselling-dev/app/adapters/ebay.py`

`/v1/trial/live` は上記アダプタを経由して取得し、既存パイプラインへ投入する。

`/v1/trial/live` の重複スキャン抑止:
- `scan_states` で `source_cursor / market_cursor` を管理し、次回の取得開始位置を前進
- `source_scan_histories` で「直近見込みなし」の商品を `scan_cooldown_minutes` 中は再処理しない
- これによりAPI使用量を抑えつつ、新しい範囲を優先探索

Cloudflare Worker UIは `BACKEND_BASE_URL` 経由でFastAPIへプロキシし、以下を1画面で運用する:
- 候補抽出 (`/v1/trial/live`)
- 人手レビュー (`/v1/review/*`)
- 分析 (`/v1/analysis/*`)
- API使用率可視化 (`/v1/analysis/api-usage`)

## 判定パイプライン
1. 仕入れ商品を取得
2. 候補市場商品を抽出
3. 一致スコア算出
4. 付属品リスク算出
5. 利益計算
6. ルールベース意思決定
7. 判定理由の保存
8. 人手レビュー確定 (必要時)

## 保守性を高めるための設計ポイント
- ルールは `services` に隔離
- 閾値は `.env` 経由で変更可能
- `decision_trace` で再現性を確保
- まずルールで運用し、後でモデル差し替え
- スケジューラは `BatchJob/BatchRun` を永続化し再実行可能性を維持
