# コーディングエージェント向けガイド

最終更新: 2026-02-10

## 目的
- 修正時に破壊的変更を避ける
- 仕様と実装の不整合を防ぐ

## 変更時の必須手順
1. 影響箇所を特定 (`api`, `services`, `db`)
2. まずテストを追加/更新
3. 実装変更
4. `pytest -q` 実行
5. 関連mdを更新
6. `docs/CHANGELOG.md` に記録

## 変更別の更新対象
- API変更: `docs/API_SPEC.md`
- 判定ロジック変更: `docs/DECISION_LOGIC.md`
- テーブル変更: `docs/DATA_MODEL.md`
- 運用手順変更: `docs/OPERATIONS.md`
- 全体設計変更: `docs/ARCHITECTURE.md`
- Cloudflare UI変更: `docs/CLOUDFLARE_UI.md`

## コード規約
- 1モジュール1責務
- 閾値は設定化してハードコード回避
- 判定理由は必ずトレースに残す
- 外部API実装は `app/adapters` に閉じ込める

## リリース前チェック
- APIが起動する
- E2Eテストが通る
- 接続診断(`scripts/check_live_connectivity.py`)が期待どおり
- `human_review` Queue/APIが機能する
- ドキュメントが最新
