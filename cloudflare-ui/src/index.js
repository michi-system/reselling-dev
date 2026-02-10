const HTML = `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Reselling Desk</title>
  <style>
    :root {
      --bg: #f2f2ef;
      --card: #ffffff;
      --ink: #17191d;
      --muted: #5f6670;
      --line: #d8d2c7;
      --primary: #005cb9;
      --accent: #0d8f83;
      --good: #1d8747;
      --bad: #b53030;
      --warn: #9a6400;
      --radius: 14px;
      --shadow: 0 12px 28px rgba(20, 16, 9, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      font-family: "BIZ UDPGothic", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
      background:
        radial-gradient(circle at 12% 8%, #d8e8ff 0%, transparent 34%),
        radial-gradient(circle at 90% 16%, #d6fff3 0%, transparent 30%),
        var(--bg);
      min-height: 100vh;
    }

    .container {
      max-width: 1360px;
      margin: 0 auto;
      padding: 20px;
      display: grid;
      gap: 14px;
    }

    .hero {
      background: linear-gradient(135deg, #0e1b3d 0%, #005cb9 45%, #0d8f83 100%);
      color: #fff;
      border-radius: var(--radius);
      padding: 18px 20px;
      box-shadow: var(--shadow);
    }
    .hero h1 { margin: 0 0 6px; font-size: 1.5rem; }
    .hero p { margin: 0; opacity: 0.93; }

    .layout {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 14px;
    }

    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 14px;
    }

    .card h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
    }

    .guide {
      display: grid;
      gap: 8px;
      margin-top: 4px;
      padding: 10px;
      background: #f8fbff;
      border: 1px solid #c7dcff;
      border-radius: 10px;
    }

    .guide .step {
      display: grid;
      grid-template-columns: 30px 1fr;
      gap: 8px;
      align-items: start;
    }

    .badge {
      width: 30px;
      height: 30px;
      border-radius: 999px;
      display: grid;
      place-items: center;
      background: #0e366b;
      color: #fff;
      font-weight: 700;
      font-size: 12px;
    }

    .grid-form {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }

    label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      font-size: 14px;
      background: #fff;
    }

    .btn-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }

    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 13px;
      font-weight: 600;
      font-family: inherit;
      cursor: pointer;
    }

    .primary { background: var(--primary); color: #fff; }
    .neutral { background: #e8edf5; color: #1b2740; }
    .approve { background: var(--good); color: #fff; }
    .reject { background: var(--bad); color: #fff; }
    .compare { background: var(--accent); color: #fff; }
    .ghost { background: #f7f4ee; color: #3c3222; }

    .metrics {
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }

    .threshold-box {
      margin-top: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fcfbf8;
      padding: 8px 10px;
    }

    .threshold-box summary {
      cursor: pointer;
      color: #22395f;
      font-size: 12px;
      font-weight: 600;
      user-select: none;
      list-style: none;
    }

    .threshold-grid {
      margin-top: 8px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }

    .metric {
      border: 1px solid var(--line);
      background: #fcfbf8;
      border-radius: 10px;
      padding: 9px;
    }

    .metric .k { color: var(--muted); font-size: 11px; }
    .metric .v { font-size: 18px; font-weight: 800; margin-top: 2px; }

    .metric-note {
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
      border: 1px dashed #d7d2c9;
      border-radius: 8px;
      padding: 7px 9px;
      background: #fcfbf8;
    }

    .status-strip {
      margin-top: 10px;
      border: 1px solid #c9d9ef;
      border-radius: 10px;
      background: #f3f9ff;
      padding: 9px;
      font-size: 13px;
    }

    .review-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }

    .review-count {
      font-size: 12px;
      color: var(--muted);
      padding: 4px 8px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f7f3ec;
    }

    .review-card-list {
      display: grid;
      gap: 10px;
    }

    .review-card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fcfbf8;
      padding: 10px;
      display: grid;
      gap: 8px;
    }

    .review-card-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      font-size: 12px;
    }

    .review-card-grid {
      display: grid;
      grid-template-columns: 1.2fr 1.2fr 1.1fr;
      gap: 10px;
      align-items: start;
    }

    .review-col {
      border: 1px solid #e8e1d5;
      border-radius: 10px;
      padding: 8px;
      background: #fff;
    }

    .review-col .title {
      font-size: 13px;
      font-weight: 600;
      line-height: 1.45;
      margin-bottom: 4px;
      word-break: break-word;
    }

    .empty-note {
      border: 1px dashed #d7d2c9;
      border-radius: 10px;
      padding: 10px;
      color: var(--muted);
      background: #fcfbf8;
      font-size: 13px;
    }

    .small { font-size: 11px; color: var(--muted); }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }

    .pill {
      display: inline-block;
      border-radius: 999px;
      font-size: 10px;
      padding: 3px 8px;
      font-weight: 700;
      margin-top: 4px;
      margin-right: 4px;
    }

    .pill.warn { background: #fff0d0; color: #875500; }
    .pill.ok { background: #dff6e7; color: #125c33; }

    .tip {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border-radius: 999px;
      border: 1px solid #8aa5c7;
      color: #30517a;
      font-size: 11px;
      font-weight: 700;
      margin-left: 4px;
      cursor: help;
      background: #eef5ff;
    }

    .usage-list {
      display: grid;
      gap: 8px;
      margin-top: 8px;
    }

    .usage-item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: #fcfbf8;
    }

    .usage-head {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      margin-bottom: 4px;
    }

    .usage-bar {
      width: 100%;
      height: 8px;
      border-radius: 999px;
      background: #e9e5dd;
      overflow: hidden;
    }

    .usage-fill {
      height: 100%;
      background: linear-gradient(90deg, #0d8f83, #d18d1f, #b53030);
      width: 0%;
      transition: width 0.2s;
    }

    .category-chip-row {
      margin: 6px 0 10px;
    }

    .category-chip-list {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .category-chip {
      border: 1px solid #c4d3e8;
      border-radius: 999px;
      background: #fff;
      color: #20456d;
      font-size: 13px;
      font-weight: 400;
      padding: 6px 10px;
      cursor: pointer;
    }

    .category-chip.active {
      background: #005cb9;
      color: #fff;
      border-color: #005cb9;
    }

    .category-picker {
      position: relative;
    }

    .category-picker-toggle {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px;
      font-size: 14px;
      font-weight: 400;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
    }

    .category-picker-panel {
      position: absolute;
      left: 0;
      right: 0;
      top: calc(100% + 6px);
      z-index: 20;
      border: 1px solid #c9d9ef;
      border-radius: 10px;
      background: #fff;
      box-shadow: var(--shadow);
      padding: 8px;
      display: none;
      gap: 6px;
    }

    .category-picker-panel.open {
      display: grid;
    }

    .category-picker-search {
      border: 1px solid #ccd8ea;
      border-radius: 8px;
      padding: 8px;
      font-size: 13px;
    }

    .category-picker-list {
      display: grid;
      gap: 4px;
      max-height: 220px;
      overflow: auto;
    }

    .category-option {
      border: 1px solid #dbe4ef;
      border-radius: 8px;
      background: #f8fbff;
      text-align: left;
      padding: 8px;
      cursor: pointer;
      font-size: 13px;
      font-family: inherit;
      font-weight: 400;
    }

    .category-option .category-option-title {
      display: block;
      font-size: 13px;
      color: #1a3553;
      font-weight: 400;
      margin-bottom: 2px;
    }

    .category-option.active {
      border-color: #005cb9;
      background: #eaf3ff;
    }

    .side h3 {
      margin: 8px 0 6px;
      font-size: 0.95rem;
    }

    .list {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 5px;
      font-size: 13px;
    }

    #status {
      border: 1px solid #2f3d58;
      border-radius: 10px;
      background: #111927;
      color: #d8e3f9;
      min-height: 130px;
      max-height: 220px;
      overflow: auto;
      white-space: pre-wrap;
      padding: 10px;
      font-size: 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }

    .compare-panel {
      display: none;
      gap: 8px;
      margin-top: 10px;
    }

    .compare-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }

    .compare-cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .compare-card {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #faf8f3;
      padding: 10px;
      display: grid;
      gap: 6px;
      align-content: start;
      min-height: 120px;
    }

    .compare-title {
      font-size: 13px;
      line-height: 1.5;
      color: #1a3553;
      font-weight: 500;
    }

    .compare-meta {
      font-size: 11px;
      color: var(--muted);
      word-break: break-all;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }

    .danger-note {
      margin-top: 6px;
      font-size: 11px;
      color: #7d4f00;
      background: #fff4dd;
      border: 1px solid #f0d7a6;
      border-radius: 8px;
      padding: 6px 8px;
    }

    .frame-label {
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }

    .link-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 5px;
    }

    a.link-btn {
      text-decoration: none;
      padding: 6px 8px;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #faf8f2;
      color: #1d2535;
      font-size: 11px;
      font-weight: 600;
    }

    a.link-btn[aria-disabled="true"] {
      pointer-events: none;
      opacity: 0.5;
    }

    @media (max-width: 1100px) {
      .layout { grid-template-columns: 1fr; }
      .grid-form { grid-template-columns: repeat(2, 1fr); }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      .threshold-grid { grid-template-columns: repeat(2, 1fr); }
      .review-card-grid { grid-template-columns: repeat(2, 1fr); }
      .compare-cards { grid-template-columns: 1fr; }
    }

    @media (max-width: 640px) {
      .grid-form { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
      .threshold-grid { grid-template-columns: 1fr; }
      .review-card-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="container">
    <section class="hero">
      <h1>Reselling Desk</h1>
      <p>仕入れ候補を抽出して確認する画面。</p>
    </section>

    <section class="layout">
      <section style="display:grid; gap: 14px;">
        <article class="card">
          <h2>1. 候補抽出</h2>
          <div class="category-chip-row">
            <div id="category-chip-bar" class="category-chip-list"></div>
          </div>
          <div class="grid-form">
            <div>
              <label>仕入れ元サイト <span class="tip" title="選択した仕入れサイトで検索します。">?</span></label>
              <select id="source_site">
                <option value="yahoo">Yahoo</option>
                <option value="rakuten">Rakuten</option>
              </select>
            </div>
            <div>
              <label>販売先サイト <span class="tip" title="比較対象の販売先です。現在はeBay固定です。">?</span></label>
              <select id="market_source">
                <option value="ebay">eBay</option>
              </select>
            </div>
            <div>
              <label>キーワード <span class="tip" title="例: sony speaker / canon lens">?</span></label>
              <input id="query" value="sony speaker" />
            </div>
            <div>
              <label>カテゴリ <span class="tip" title="カテゴリ候補から選択">?</span></label>
              <div class="category-picker">
                <button id="category_picker_toggle" class="category-picker-toggle" type="button">audio</button>
                <div id="category_picker_panel" class="category-picker-panel">
                  <div id="category_picker_list" class="category-picker-list"></div>
                </div>
              </div>
              <input id="category" value="audio" type="hidden" />
              <div id="category_hint" class="small" style="margin-top:4px; display:none;"></div>
            </div>
            <div>
              <label><span id="count-sync-label-text">比較件数（仕入れ/eBay同期）</span> <span id="count-sync-tip" class="tip" title="1〜100。仕入れサイトとeBayを同じ件数で取得し、取得分を全件判定します">?</span></label>
              <input id="source_limit" type="number" value="5" min="1" max="1000" />
            </div>
            <div>
              <label>商品状態 <span class="tip" title="新品/中古を指定。仕入れ側と販売側の状態が一致しない組み合わせは見送りにします。">?</span></label>
              <select id="item_condition">
                <option value="any">指定なし（新品/中古）</option>
                <option value="new">新品のみ</option>
                <option value="used">中古のみ</option>
              </select>
            </div>
            <div>
              <label>再スキャン抑止(分)</label>
              <input id="scan_cooldown_minutes" type="number" value="60" min="1" max="1440" />
            </div>
          </div>
          <div class="btn-row">
            <button id="preset-accuracy" class="ghost">おすすめ</button>
            <button id="run-trial" class="primary">抽出</button>
            <button id="reset-scan-state" class="ghost">先頭から再開</button>
            <button id="refresh-all" class="neutral">更新</button>
          </div>
          <details class="threshold-box">
            <summary>閾値を調整</summary>
            <div class="threshold-grid">
              <div>
                <label>自動採用 一致度</label>
                <input id="th_min_auto_accept_score" type="number" min="0" max="1" step="0.01" value="0.85" />
              </div>
              <div>
                <label>要確認 一致度</label>
                <input id="th_min_human_review_score" type="number" min="0" max="1" step="0.01" value="0.40" />
              </div>
              <div>
                <label>最低利益(円)</label>
                <input id="th_min_expected_profit_jpy" type="number" min="-1000000" max="100000000" step="50" value="0" />
              </div>
              <div>
                <label>最低利益率</label>
                <input id="th_min_expected_margin_rate" type="number" min="0" max="1" step="0.01" value="0.10" />
              </div>
            </div>
            <div class="btn-row" style="margin-top:8px;">
              <button id="reset-thresholds" class="ghost">既定値に戻す</button>
            </div>
          </details>

          <div class="metrics">
            <div class="metric"><div class="k">今回判定</div><div class="v" id="m-judge">-</div></div>
            <div class="metric"><div class="k">累積判定</div><div class="v" id="m-combo">-</div></div>
            <div class="metric"><div class="k" id="m-cursor-label">次回位置</div><div class="v" id="m-cursor">-</div></div>
          </div>
          <div id="m-combo-note" class="metric-note">累積: 仕入れ - 件 / 販売参照 - 件 / 判定 - 件</div>
          <div id="m-fetch-note" class="metric-note">今回: 判定 - 件 / 販売参照 - 件 / スキップ - 件</div>

          <div id="session-status" class="status-strip">準備完了</div>
        </article>

        <article class="card">
          <div class="review-header">
            <h2>2. 人手レビュー</h2>
            <div id="queue-count" class="review-count">累積 - 件</div>
          </div>
          <div class="small" style="margin-bottom:8px;">リンク確認して承認/却下 <span class="tip" title="同一商品なら承認。別商品や付属品は却下。">?</span></div>

          <div class="grid-form" style="grid-template-columns: 1fr 2fr; margin-bottom: 8px;">
            <div>
              <label>レビュー担当者</label>
              <input id="reviewer" value="owner" />
            </div>
            <div>
              <label>メモ (任意)</label>
              <input id="review-note" placeholder="例: 型番と付属品有無を確認" />
            </div>
          </div>

          <div class="btn-row" style="margin-top: 0; margin-bottom: 8px;">
            <button id="refresh-queue" class="neutral">キュー更新</button>
          </div>

          <div id="review-body" class="review-card-list"></div>
        </article>
      </section>

      <aside class="side" style="display:grid; gap:14px; align-content:start;">
        <article class="card">
          <h2>3. 見送り分析（累積）</h2>
          <h3>見送り理由</h3>
          <ul id="reject-list" class="list"></ul>
        </article>

        <article class="card">
          <h2>API使用率<span class="tip" title="eBayは公式Rate Limits APIの上限窓を使用。観測回数(直近60分)とは別軸です。Yahoo/楽天は公式残量APIがないため、観測回数とローカル抑止設定ベースで表示します。">?</span></h2>
          <div class="btn-row" style="margin-top:0;">
            <button id="refresh-usage" class="neutral">使用率を更新</button>
          </div>
          <div id="usage-list" class="usage-list"></div>
        </article>

        <article class="card">
          <h2>イベントログ</h2>
          <div id="status"></div>
        </article>
      </aside>
    </section>
  </main>

  <script>
    var state = {
      categorySuggestions: [],
      lastRunHumanReviewCount: null,
      hasExecutedTrial: false,
      lastRunAtIso: "",
      lastRunAnalysis: null,
      scanSummary: null,
      defaultThresholds: null
    };

    function el(id) {
      return document.getElementById(id);
    }

    function now() {
      return new Date().toLocaleTimeString();
    }

    function log(message) {
      var node = el("status");
      node.textContent += "[" + now() + "] " + message + "\\n";
      node.scrollTop = node.scrollHeight;
    }

    function setSessionStatus(message) {
      el("session-status").textContent = message;
    }

    function resetRunScopedPanels() {
      var sourceName = selectedSourceSiteLabel();
      state.lastRunAnalysis = null;
      state.scanSummary = null;
      state.lastRunHumanReviewCount = null;
      state.hasExecutedTrial = false;
      el("m-judge").textContent = "-";
      el("m-combo").textContent = "-";
      el("m-cursor").textContent = "-";
      el("m-cursor-label").textContent = "次回位置";
      el("m-combo-note").textContent = "累積: 仕入れ - 件 / 販売参照 - 件 / 判定 - 件";
      el("m-fetch-note").textContent = "今回(" + sourceName + "): 判定 - 件 / 販売参照 - 件 / スキップ - 件";
      loadAnalysis().catch(function (_error) {});
      loadReviewQueue().catch(function (_error) {});
    }

    function escapeHtml(value) {
      return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function formatYen(value) {
      var num = Number(value || 0);
      return Math.round(num).toLocaleString("ja-JP") + "円";
    }

    function formatPct(value) {
      var num = Number(value || 0) * 100;
      return num.toFixed(1) + "%";
    }

    function parseTrace(traceStr) {
      try {
        return JSON.parse(traceStr || "{}");
      } catch (_error) {
        return {};
      }
    }

    function siteLabel(raw) {
      var value = String(raw || "").toLowerCase();
      if (value.indexOf("mock") >= 0) {
        return "テストデータ";
      }
      if (value.indexOf("yahoo") >= 0) {
        return "Yahoo";
      }
      if (value.indexOf("rakuten") >= 0) {
        return "楽天";
      }
      if (value.indexOf("ebay") >= 0) {
        return "eBay";
      }
      if (value.indexOf("mercari") >= 0) {
        return "メルカリ";
      }
      return raw || "-";
    }

    function selectedSourceSiteLabel() {
      var node = el("source_site");
      if (!node) {
        return "仕入れサイト";
      }
      return siteLabel(node.value || "");
    }

    function syncSourceSiteUiLabels() {
      var sourceName = selectedSourceSiteLabel();
      var countLabel = el("count-sync-label-text");
      var countTip = el("count-sync-tip");
      if (countLabel) {
        countLabel.textContent = "比較件数（" + sourceName + "/eBay同期）";
      }
      if (countTip) {
        countTip.title = "1〜100。" + sourceName + "とeBayを同じ件数で取得し、取得分を全件判定します";
      }
    }

    function reasonLabel(code) {
      if (code === "cross_market_to_ebay") {
        return selectedSourceSiteLabel() + "からeBayへの横断比較（注意）";
      }
      var map = {
        accessory_risk_high: "付属品・別商品の可能性が高い",
        profit_below_threshold: "利益が最低基準を下回る",
        margin_below_threshold: "利益率が最低基準を下回る",
        title_similarity_low: "商品名の一致度が低い",
        match_score_low: "一致スコアが低い",
        price_confidence_low: "価格データの信頼度が低い",
        rule_gate_failed: "判定ルールを満たさない",
        compliance_block_auto_accept: "規約ガードにより自動採用を停止",
        compliance_force_human_review: "規約ガードにより人手確認へ変更",
        mercari_terms_sensitive_source: "メルカリ由来データの規約注意",
        rakuten_usage_terms_check_required: "楽天データの利用条件を要確認",
        condition_pair_mismatch: "新品/中古の組み合わせが不一致",
        source_condition_filter_mismatch: "仕入れ側が指定した商品状態と不一致",
        market_condition_filter_mismatch: "販売側が指定した商品状態と不一致",
        trace_parse_error: "判定ログの解析エラー",
        unknown: "不明"
      };
      if (!code) {
        return "なし";
      }
      return map[code] || code;
    }

    function closeCategoryPicker() {
      el("category_picker_panel").classList.remove("open");
      el("category_hint").style.display = "none";
    }

    function openCategoryPicker() {
      el("category_picker_panel").classList.add("open");
      el("category_hint").style.display = "block";
    }

    function updateCategoryPickerLabel() {
      var categoryValue = String(el("category").value || "").trim();
      var selected = null;
      for (var i = 0; i < state.categorySuggestions.length; i += 1) {
        if (String(state.categorySuggestions[i].internal_category).toLowerCase() === categoryValue.toLowerCase()) {
          selected = state.categorySuggestions[i];
          break;
        }
      }
      if (selected) {
        el("category_picker_toggle").textContent = selected.label_ja + " (" + selected.internal_category + ")";
      } else {
        el("category_picker_toggle").textContent = categoryValue || "カテゴリを選択";
      }
    }

    function setCategoryHint(item) {
      var hintNode = el("category_hint");
      if (!item) {
        hintNode.textContent = "";
        return;
      }
      hintNode.textContent = "仕入れ元候補: " + (item.source_hint || "なし")
        + " / 販売先候補: " + (item.market_hint || "なし");
    }

    function selectCategory(category, label, item) {
      el("category").value = category;
      updateCategoryPickerLabel();
      setCategoryHint(item || null);
      setSessionStatus("カテゴリを選択: " + label + " (" + category + ")");
      renderCategorySuggestions(state.categorySuggestions);
      closeCategoryPicker();
      loadTrialSummary()
        .then(function () { return loadAnalysis(); })
        .catch(function (error) { log("カテゴリ変更後の集計更新失敗: " + error.message); });
    }

    function renderCategorySuggestions(items) {
      var chipBar = el("category-chip-bar");
      var pickerList = el("category_picker_list");
      var selectedCategory = String(el("category").value || "").trim().toLowerCase();
      chipBar.innerHTML = "";
      pickerList.innerHTML = "";

      if (!items.length) {
        pickerList.innerHTML = "<div class='small'>候補がありません</div>";
        setCategoryHint(null);
        updateCategoryPickerLabel();
        return;
      }

      var selectedItem = null;
      for (var i = 0; i < items.length; i += 1) {
        if (String(items[i].internal_category).toLowerCase() === selectedCategory) {
          selectedItem = items[i];
          break;
        }
      }

      var topItems = items.slice(0, 8);
      for (var j = 0; j < topItems.length; j += 1) {
        var chipItem = topItems[j];
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "category-chip" + (chipItem.internal_category.toLowerCase() === selectedCategory ? " active" : "");
        chip.textContent = chipItem.label_ja;
        chip.addEventListener("click", (function (row) {
          return function () {
            selectCategory(row.internal_category, row.label_ja, row);
          };
        })(chipItem));
        chipBar.appendChild(chip);
      }

      for (var k = 0; k < items.length; k += 1) {
        var row = items[k];
        var button = document.createElement("button");
        button.type = "button";
        button.className = "category-option" + (row.internal_category.toLowerCase() === selectedCategory ? " active" : "");
        button.innerHTML =
          "<span class='category-option-title'>" + escapeHtml(row.label_ja) + "</span>"
          + "<div>内部コード: " + escapeHtml(row.internal_category) + "</div>"
          + "<div class='small'>仕入れ元: " + escapeHtml(row.source_hint || "なし") + "</div>"
          + "<div class='small'>販売先: " + escapeHtml(row.market_hint || "なし") + "</div>";
        button.addEventListener("click", (function (picked) {
          return function () {
            selectCategory(picked.internal_category, picked.label_ja, picked);
          };
        })(row));
        pickerList.appendChild(button);
      }

      setCategoryHint(selectedItem || items[0]);
      updateCategoryPickerLabel();
    }

    async function loadCategorySuggestions() {
      var params = new URLSearchParams({
        source_site: el("source_site").value,
        market_source: el("market_source").value,
        query: el("query").value || "",
        selected_category: el("category").value || "",
        limit: "60"
      });
      var response = await api("/api/categories/suggestions?" + params.toString());
      state.categorySuggestions = Array.isArray(response.items) ? response.items : [];
      renderCategorySuggestions(state.categorySuggestions);
    }

    async function api(path, options) {
      var response = await fetch(path, options || {});
      var text = await response.text();
      var body;
      try {
        body = text ? JSON.parse(text) : {};
      } catch (_error) {
        body = { raw: text };
      }

      if (!response.ok) {
        var detail = body && (body.detail || body.raw) ? (body.detail || body.raw) : JSON.stringify(body);
        throw new Error(String(response.status) + " " + detail);
      }
      return body;
    }

    function collectTrialPayload() {
      var sourceLimit = Number(el("source_limit").value);
      return {
        source_site: el("source_site").value,
        market_source: el("market_source").value,
        query: el("query").value,
        category: el("category").value,
        source_limit: sourceLimit,
        market_limit: sourceLimit,
        run_pipeline_top_n: sourceLimit,
        scan_cooldown_minutes: Number(el("scan_cooldown_minutes").value),
        item_condition: el("item_condition").value,
        thresholds: collectThresholdPayload()
      };
    }

    function collectThresholdPayload() {
      return {
        min_auto_accept_score: Number(el("th_min_auto_accept_score").value),
        min_human_review_score: Number(el("th_min_human_review_score").value),
        min_expected_profit_jpy: Number(el("th_min_expected_profit_jpy").value),
        min_expected_margin_rate: Number(el("th_min_expected_margin_rate").value)
      };
    }

    function applyThresholdInputs(data) {
      if (!data) {
        return;
      }
      el("th_min_auto_accept_score").value = String(Number(data.min_auto_accept_score || 0).toFixed(2));
      el("th_min_human_review_score").value = String(Number(data.min_human_review_score || 0).toFixed(2));
      el("th_min_expected_profit_jpy").value = String(Math.round(Number(data.min_expected_profit_jpy || 0)));
      el("th_min_expected_margin_rate").value = String(Number(data.min_expected_margin_rate || 0).toFixed(2));
    }

    async function loadThresholdSettings() {
      var params = new URLSearchParams({
        category: String(el("category").value || "")
      });
      var current = await api("/api/system/thresholds?" + params.toString());
      state.defaultThresholds = current;
      applyThresholdInputs(current);
      return current;
    }

    function normalizeTrialPayload(payload) {
      var sourceMax = 100;
      var originalSourceLimit = payload.source_limit;
      var originalCooldown = payload.scan_cooldown_minutes;

      payload.source_limit = Math.max(1, Math.min(Number(payload.source_limit || 1), sourceMax));
      payload.market_limit = payload.source_limit;
      payload.run_pipeline_top_n = payload.source_limit;
      payload.scan_cooldown_minutes = Math.max(1, Math.min(Number(payload.scan_cooldown_minutes || 60), 1440));

      el("source_limit").value = String(payload.source_limit);
      el("scan_cooldown_minutes").value = String(payload.scan_cooldown_minutes);

      if (
        payload.source_limit !== originalSourceLimit
        || payload.scan_cooldown_minutes !== originalCooldown
      ) {
        log(
          "入力値を自動調整: 比較件数 " + originalSourceLimit + "→" + payload.source_limit
          + " / 再スキャン抑止(分) " + originalCooldown + "→" + payload.scan_cooldown_minutes
        );
      }

      return payload;
    }

    function applyAccuracyPreset() {
      el("source_limit").value = "8";
      el("scan_cooldown_minutes").value = "60";
      el("item_condition").value = "any";
      setSessionStatus("推奨値を適用しました。");
      log("おすすめ値を適用 count=8 cooldown=60 item_condition=any");
    }

    function renderMetrics(result) {
      var sourceName = selectedSourceSiteLabel();
      var marketName = siteLabel(el("market_source").value || "ebay");
      var runs = Array.isArray(result.source_runs) ? result.source_runs : [];
      var autoAccept = 0; // product-level count
      var humanReview = 0; // product-level count
      var reject = 0; // product-level count
      for (var i = 0; i < runs.length; i += 1) {
        var run = runs[i];
        var hasAutoAccept = Number(run.auto_accept_count || 0) > 0;
        var hasHumanReview = Number(run.human_review_count || 0) > 0;
        if (hasAutoAccept) {
          autoAccept += 1;
        } else if (hasHumanReview) {
          humanReview += 1;
        } else {
          reject += 1;
        }
      }
      el("m-judge").textContent = "採用 " + autoAccept + " / 要確認 " + humanReview + " / 見送り " + reject;
      state.lastRunHumanReviewCount = humanReview;
      state.hasExecutedTrial = true;
      state.lastRunAtIso = new Date().toISOString();

      el("m-fetch-note").textContent =
        "今回(" + sourceName + "): 判定 " + String(result.processed_source_items || 0)
        + " 件 / " + marketName + "参照 " + String(result.imported_market_items || 0)
        + " 件 / スキップ " + String(result.skipped_recent_source_items || 0) + " 件";

      var sourceCursor = Number(result.source_cursor || 0);
      var marketCursor = Number(result.market_cursor || 0);
      if (sourceCursor < 0 && marketCursor < 0) {
        el("m-cursor").textContent = "全範囲確認済み";
      } else {
        var sourceCountText = sourceCursor < 0
          ? (sourceName + ": 完了")
          : (sourceName + ": " + sourceCursor + "件目");
        var marketCountText = marketCursor < 0
          ? (marketName + ": 完了")
          : (marketName + ": " + marketCursor + "件目");
        el("m-cursor").textContent = sourceCountText + " / " + marketCountText;
      }
      el("m-cursor-label").textContent = "次回位置";

      if (sourceCursor < 0 && marketCursor < 0) {
        setSessionStatus("抽出完了: 全範囲確認済み");
        return;
      }
      setSessionStatus(
        "抽出完了: 判定 " + (result.processed_source_items || 0)
        + "件 / 要確認 " + humanReview + "件"
      );
    }

    function collectSummaryParams() {
      return {
        source_site: el("source_site").value,
        market_source: el("market_source").value,
        query: el("query").value,
        category: el("category").value,
        item_condition: el("item_condition").value
      };
    }

    async function loadTrialSummary() {
      var payload = collectSummaryParams();
      if (!String(payload.query || "").trim() || !String(payload.category || "").trim()) {
        state.scanSummary = null;
        el("m-combo").textContent = "-";
        return null;
      }
      var params = new URLSearchParams(payload);
      var summary = await api("/api/trial/summary?" + params.toString());
      state.scanSummary = summary;

      var pairAuto = Number(summary.pair_auto_accept_total || 0);
      var pairHuman = Number(summary.pair_human_review_total || 0);
      var pairReject = Number(summary.pair_reject_total || 0);
      el("m-combo").textContent = "採用 " + pairAuto + " / 要確認 " + pairHuman + " / 見送り " + pairReject;
      var importedSource = Number(summary.total_source_items_imported || 0);
      var importedMarket = Number(summary.total_market_items_imported || 0);
      var processedSource = Number(summary.total_source_items_processed || 0);
      var summarySourceName = selectedSourceSiteLabel();
      var summaryMarketName = siteLabel(el("market_source").value || "ebay");
      if (importedSource === 0 && importedMarket === 0 && processedSource > 0) {
        el("m-combo-note").textContent =
          "累積: 旧データ(取得未記録) / 判定 " + processedSource + " 件";
      } else {
        el("m-combo-note").textContent =
          "累積: " + summarySourceName + " " + importedSource
          + " 件 / " + summaryMarketName + "参照 " + importedMarket
          + " 件 / 判定 " + processedSource + " 件";
      }
      return summary;
    }

    async function runTrial() {
      var payload = normalizeTrialPayload(collectTrialPayload());
      setSessionStatus("抽出中...");
      log("候補抽出開始 query=" + payload.query + " category=" + payload.category + " condition=" + payload.item_condition);
      var usageBefore = await api("/api/analysis/api-usage");

      var result = await api("/api/trial/live", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });

      renderMetrics(result);
      state.lastRunAnalysis = {
        totalRejects: Number(result.run_total_rejects || 0),
        rejectReasons: Array.isArray(result.run_reject_reasons) ? result.run_reject_reasons : [],
        totalCompliance: Number(result.run_total_compliance_flagged || 0),
        complianceReasons: Array.isArray(result.run_compliance_reasons) ? result.run_compliance_reasons : []
      };
      log("候補抽出完了 source=" + result.imported_source_items + " market=" + result.imported_market_items + " skipped=" + (result.skipped_recent_source_items || 0));
      await Promise.all([loadReviewQueue(), loadTrialSummary()]);
      await loadAnalysis();
      var usageAfter = await loadApiUsage();
      var deltaLog = buildUsageDeltaLog(usageBefore, usageAfter);
      if (deltaLog) {
        log(deltaLog);
      }
    }

    async function resetScanStateForCurrentCondition() {
      var payload = collectSummaryParams();
      if (!String(payload.query || "").trim() || !String(payload.category || "").trim()) {
        setSessionStatus("キーワードとカテゴリを入力してから実行してください。");
        return;
      }
      await api("/api/trial/reset-state", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload)
      });

      resetRunScopedPanels();
      await Promise.all([loadTrialSummary(), loadAnalysis()]);
      el("m-cursor").textContent = selectedSourceSiteLabel() + ": 0件 / " + siteLabel(el("market_source").value || "ebay") + ": 0件";
      setSessionStatus("検索位置を先頭に戻しました");
      log("検索位置を先頭へリセット query=" + payload.query + " category=" + payload.category);
    }

    function toUsageMap(snapshot) {
      var map = {};
      var items = snapshot && Array.isArray(snapshot.items) ? snapshot.items : [];
      for (var i = 0; i < items.length; i += 1) {
        var item = items[i];
        map[String(item.provider || "")] = Number(item.calls_last_hour || 0);
      }
      return map;
    }

    function buildUsageDeltaLog(beforeSnapshot, afterSnapshot) {
      var before = toUsageMap(beforeSnapshot);
      var after = toUsageMap(afterSnapshot);
      var providers = ["yahoo", "rakuten", "ebay"];
      var chunks = [];
      for (var i = 0; i < providers.length; i += 1) {
        var provider = providers[i];
        var delta = (after[provider] || 0) - (before[provider] || 0);
        if (delta > 0) {
          chunks.push(providerLabel(provider) + " +" + delta);
        }
      }
      if (!chunks.length) {
        return "";
      }
      return "今回のAPI増分: " + chunks.join(" / ");
    }

    function rowHtml(item) {
      var trace = parseTrace(item.decision_trace);
      var reason = trace.reject_reason ? String(trace.reject_reason) : "";
      var sourceLink = item.source_link || "";
      var marketLink = item.market_link || "";
      var sourceSiteName = siteLabel(item.source_site);
      var marketSiteName = siteLabel(item.market_site);
      var sourceTotal = Number(item.source_price_jpy || 0) + Number(item.source_shipping_jpy || 0);
      var marketUsdTotal = Number(item.market_price_usd || 0) + Number(item.market_shipping_usd || 0);
      var marketRevenueJpy = Number(item.market_revenue_jpy || 0);
      var conditionSummary = "状態: " + escapeHtml(item.source_condition || "unknown") + " / " + escapeHtml(item.market_condition || "unknown");
      var categorySummary = "カテゴリ: " + escapeHtml(item.source_category || "-") + " / " + escapeHtml(item.market_category || "-");
      var summaryLine = conditionSummary + "<br>" + categorySummary;
      var traceMatch = Array.isArray(trace.match_reasons) ? trace.match_reasons.slice(0, 3).join(" / ") : "";
      return '' +
        '<article class="review-card">' +
          '<div class="review-card-head">' +
            '<div><span class="small">比較ID</span> <b>#' + item.opportunity_id + '</b></div>' +
            '<div class="small">' + new Date(item.created_at).toLocaleString() + '</div>' +
          '</div>' +
          '<div class="review-card-grid">' +
            '<section class="review-col">' +
              '<div class="small">' + escapeHtml(sourceSiteName) + '</div>' +
              '<div class="title">' + escapeHtml(item.source_title) + '</div>' +
              '<div class="small mono">' + escapeHtml(sourceSiteName) + ' / ' + escapeHtml(item.source_item_external_id) + '</div>' +
              '<div class="small" style="margin-top:4px;">価格: <b>' + formatYen(Number(item.source_price_jpy || 0)) + '</b> / 送料: <b>' + formatYen(Number(item.source_shipping_jpy || 0)) + '</b></div>' +
              '<div class="small">合計: <b>' + formatYen(sourceTotal) + '</b></div>' +
              '<div class="btn-row" style="margin-top:6px;">' +
                '<a class="link-btn" href="' + escapeHtml(sourceLink || "#") + '" target="_blank" rel="noopener noreferrer"' + (sourceLink ? "" : ' aria-disabled="true"') + '>' + escapeHtml(sourceSiteName) + 'を開く</a>' +
              '</div>' +
            '</section>' +
            '<section class="review-col">' +
              '<div class="small">' + escapeHtml(marketSiteName) + '</div>' +
              '<div class="title">' + escapeHtml(item.market_title) + '</div>' +
              '<div class="small mono">' + escapeHtml(marketSiteName) + ' / ' + escapeHtml(item.market_item_external_id) + '</div>' +
              '<div class="small" style="margin-top:4px;">価格: <b>$' + Number(item.market_price_usd || 0).toFixed(2) + '</b> / 送料: <b>$' + Number(item.market_shipping_usd || 0).toFixed(2) + '</b></div>' +
              '<div class="small">合計: <b>$' + marketUsdTotal.toFixed(2) + '</b> / 円換算: <b>' + formatYen(marketRevenueJpy) + '</b></div>' +
              '<div class="btn-row" style="margin-top:6px;">' +
                '<a class="link-btn" href="' + escapeHtml(marketLink || "#") + '" target="_blank" rel="noopener noreferrer"' + (marketLink ? "" : ' aria-disabled="true"') + '>' + escapeHtml(marketSiteName) + 'を開く</a>' +
              '</div>' +
            '</section>' +
            '<section class="review-col">' +
              '<div class="small">判定</div>' +
              '<div>一致度: <b>' + Number(item.match_score).toFixed(3) + '</b></div>' +
              '<div>利益率: <b>' + formatPct(item.expected_margin_rate) + '</b> / 想定利益: <b>' + formatYen(item.expected_profit_jpy) + '</b></div>' +
              '<div class="small" style="margin-top:4px;">概要: ' + summaryLine + '</div>' +
              (traceMatch ? ('<div class="small">一致根拠: ' + escapeHtml(traceMatch) + '</div>') : '') +
              '<div class="small">見送り理由: ' + escapeHtml(reasonLabel(reason)) + '</div>' +
              '<div class="btn-row" style="margin-top:8px;">' +
                '<button class="approve" data-action="approve" data-id="' + item.opportunity_id + '">承認</button>' +
                '<button class="reject" data-action="reject" data-id="' + item.opportunity_id + '">却下</button>' +
              '</div>' +
            '</section>' +
          '</div>' +
        '</article>';
    }

    async function submitReview(opportunityId, outcome) {
      var reviewer = el("reviewer").value || "owner";
      var note = el("review-note").value || "";

      await api("/api/review/" + opportunityId, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ outcome: outcome, reviewer: reviewer, note: note })
      });

      log("レビュー確定 id=" + opportunityId + " outcome=" + outcome);
      await loadReviewQueue();
    }

    async function loadReviewQueue() {
      var items = await api("/api/review/queue?limit=100");
      var body = el("review-body");
      body.innerHTML = "";

      if (state.hasExecutedTrial) {
        var thisRunCount = state.lastRunHumanReviewCount == null ? "-" : String(state.lastRunHumanReviewCount);
        el("queue-count").textContent = "今回 " + thisRunCount + "件 / 累積 " + items.length + "件";
      } else {
        el("queue-count").textContent = "累積 " + items.length + "件";
      }

      if (state.hasExecutedTrial && state.lastRunHumanReviewCount === 0 && items.length > 0) {
        log("注記: 今回の要確認は0件ですが、過去の未処理レビューが " + items.length + "件あります。");
      }

      if (!items.length) {
        body.innerHTML = '<div class="empty-note">レビュー待ちはありません。</div>';
        return;
      }

      for (var i = 0; i < items.length; i += 1) {
        body.insertAdjacentHTML("beforeend", rowHtml(items[i]));
      }

      var buttons = body.querySelectorAll("button[data-action]");
      buttons.forEach(function (btn) {
        btn.addEventListener("click", async function () {
          var action = btn.getAttribute("data-action");
          var id = Number(btn.getAttribute("data-id"));
          if (action === "approve" || action === "reject") {
            try {
              await submitReview(id, action);
            } catch (error) {
              log("レビュー失敗 id=" + id + " error=" + error.message);
            }
          }
        });
      });
    }

    async function loadAnalysis() {
      var rejectList = el("reject-list");
      rejectList.innerHTML = "";
      var summary = state.scanSummary;
      var rejectItems = [];
      var totalReject = 0;

      if (summary && Number(summary.total_runs || 0) > 0) {
        rejectItems = Array.isArray(summary.reject_reasons) ? summary.reject_reasons.slice(0, 8) : [];
        totalReject = Number(summary.pair_reject_total || 0);
      } else if (state.lastRunAnalysis) {
        var run = state.lastRunAnalysis;
        rejectItems = Array.isArray(run.rejectReasons) ? run.rejectReasons.slice(0, 8) : [];
        totalReject = Number(run.totalRejects || 0);
      } else {
        rejectList.innerHTML = "<li>まだ集計がありません</li>";
        return;
      }

      if (!rejectItems.length) {
        rejectList.innerHTML = "<li>データなし</li>";
      } else {
        for (var i = 0; i < rejectItems.length; i += 1) {
          var li = document.createElement("li");
          li.textContent = reasonLabel(rejectItems[i].reason) + ": " + rejectItems[i].count;
          rejectList.appendChild(li);
        }
      }

      log("分析更新(累積) 見送り=" + totalReject);
    }

    function providerLabel(provider) {
      if (provider === "yahoo") {
        return "Yahoo";
      }
      if (provider === "rakuten") {
        return "楽天";
      }
      if (provider === "ebay") {
        return "eBay";
      }
      return provider;
    }

    async function loadApiUsage() {
      var usage = await api("/api/analysis/api-usage");
      var list = el("usage-list");
      list.innerHTML = "";

      var items = Array.isArray(usage.items) ? usage.items : [];
      if (!items.length) {
        list.innerHTML = "<div class='small'>データなし</div>";
        return usage;
      }

      for (var i = 0; i < items.length; i += 1) {
        var item = items[i];
        var hasPercent = typeof item.usage_rate_percent === "number" && Number.isFinite(item.usage_rate_percent);
        var safePercent = hasPercent ? Math.max(0, Math.min(100, Number(item.usage_rate_percent))) : 0;
        var percentLabel = hasPercent ? safePercent.toFixed(1) + "%" : "不明";
        var budgetLabel = "上限 不明";
        if (item.hourly_budget !== null && item.hourly_budget !== undefined) {
          budgetLabel = "上限 " + item.hourly_budget;
        }
        var remainLabel = "残り 不明";
        if (item.remaining_calls !== null && item.remaining_calls !== undefined) {
          remainLabel = "残り " + item.remaining_calls;
        }
        var windowLabel = String(item.limit_window || "不明");
        var basisLabel = item.usage_basis === "official"
          ? "公式"
          : (item.usage_basis === "local_throttle" ? "ローカル抑止換算" : "不明");
        var usageTipTitle = "判定基準: " + basisLabel + " / 窓: " + windowLabel + " / " + String(item.note || "");
        var counterLine = "";
        if (item.usage_basis === "official") {
          counterLine = "このアプリ直近" + usage.window_minutes + "分: " + item.calls_last_hour
            + " / 公式窓 上限 " + escapeHtml(String(item.hourly_budget !== null && item.hourly_budget !== undefined ? item.hourly_budget : "不明"))
            + " (" + escapeHtml(remainLabel) + ")";
        } else {
          counterLine = "このアプリ直近" + usage.window_minutes + "分: " + item.calls_last_hour
            + " / " + escapeHtml(budgetLabel) + " (" + escapeHtml(remainLabel) + ")";
        }

        var node = document.createElement("div");
        node.className = "usage-item";
        node.innerHTML =
          "<div class='usage-head'><div style='display:flex;align-items:center;gap:6px;'><b>" + escapeHtml(providerLabel(item.provider)) + "</b><span class='tip' title='" + escapeHtml(usageTipTitle) + "'>?</span></div><span>" + escapeHtml(percentLabel) + "</span></div>" +
          "<div class='usage-bar'><div class='usage-fill' style='width:" + safePercent.toFixed(2) + "%'></div></div>" +
          "<div class='small' style='margin-top:4px;'>" + counterLine + "</div>";
        list.appendChild(node);
      }
      return usage;
    }

    async function refreshAll() {
      await Promise.all([loadReviewQueue(), loadApiUsage(), loadTrialSummary()]);
      await loadAnalysis();
      setSessionStatus("更新完了");
    }

    function bindEvents() {
      el("preset-accuracy").addEventListener("click", function () {
        applyAccuracyPreset();
      });

      el("source_site").addEventListener("change", async function () {
        try {
          syncSourceSiteUiLabels();
          resetRunScopedPanels();
          normalizeTrialPayload(collectTrialPayload());
          await Promise.all([loadCategorySuggestions(), loadTrialSummary()]);
          await loadAnalysis();
          setSessionStatus("条件変更: 表示を更新しました");
        } catch (error) {
          log("カテゴリ候補更新失敗: " + error.message);
        }
      });

      el("market_source").addEventListener("change", async function () {
        try {
          resetRunScopedPanels();
          await Promise.all([loadCategorySuggestions(), loadTrialSummary()]);
          await loadAnalysis();
          setSessionStatus("条件変更: 表示を更新しました");
        } catch (error) {
          log("カテゴリ候補更新失敗: " + error.message);
        }
      });

      el("query").addEventListener("change", async function () {
        try {
          resetRunScopedPanels();
          await Promise.all([loadCategorySuggestions(), loadTrialSummary()]);
          await loadAnalysis();
          setSessionStatus("条件変更: 表示を更新しました");
        } catch (error) {
          log("カテゴリ候補更新失敗: " + error.message);
        }
      });

      el("category_picker_toggle").addEventListener("click", function () {
        var panel = el("category_picker_panel");
        if (panel.classList.contains("open")) {
          closeCategoryPicker();
        } else {
          openCategoryPicker();
        }
      });

      document.addEventListener("click", function (event) {
        var panel = el("category_picker_panel");
        var toggle = el("category_picker_toggle");
        if (!panel.classList.contains("open")) {
          return;
        }
        if (panel.contains(event.target) || toggle.contains(event.target)) {
          return;
        }
        closeCategoryPicker();
      });

      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          closeCategoryPicker();
        }
      });

      el("run-trial").addEventListener("click", async function () {
        try {
          await runTrial();
        } catch (error) {
          if (String(error.message || "").indexOf("422") === 0) {
            setSessionStatus("入力値エラー: 数値を確認してください");
          } else {
            setSessionStatus("抽出エラー: ログを確認してください");
          }
          log("候補抽出失敗: " + error.message);
        }
      });

      el("refresh-all").addEventListener("click", async function () {
        try {
          await refreshAll();
        } catch (error) {
          log("全体更新失敗: " + error.message);
        }
      });

      el("reset-scan-state").addEventListener("click", async function () {
        var ok = window.confirm("現在条件の検索位置を先頭に戻します。実行しますか？");
        if (!ok) {
          return;
        }
        try {
          await resetScanStateForCurrentCondition();
        } catch (error) {
          log("検索位置リセット失敗: " + error.message);
          setSessionStatus("検索位置のリセットに失敗しました");
        }
      });

      el("refresh-queue").addEventListener("click", async function () {
        try {
          await loadReviewQueue();
          setSessionStatus("レビューキューを更新しました");
        } catch (error) {
          log("キュー更新失敗: " + error.message);
        }
      });

      el("refresh-usage").addEventListener("click", async function () {
        try {
          await loadApiUsage();
          log("API使用率を更新");
        } catch (error) {
          log("API使用率更新エラー: " + error.message);
        }
      });

      el("reset-thresholds").addEventListener("click", async function () {
        try {
          await loadThresholdSettings();
          setSessionStatus("閾値を既定値に戻しました");
          log("閾値を既定値にリセット");
        } catch (error) {
          log("閾値のリセット失敗: " + error.message);
        }
      });

    }

    async function init() {
      bindEvents();
      syncSourceSiteUiLabels();
      resetRunScopedPanels();
      log("初期化開始");
      try {
        await Promise.all([refreshAll(), loadCategorySuggestions(), loadThresholdSettings()]);
        log("初期化完了");
      } catch (error) {
        setSessionStatus("初期化失敗: バックエンド接続を確認してください");
        log("初期化失敗: " + error.message);
      }
    }

    init();
  </script>
</body>
</html>`;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

function getBackendBase(env) {
  const base = String(env.BACKEND_BASE_URL || "").trim();
  if (!base) {
    return "";
  }
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

async function proxyToBackend(request, env, pathWithQuery) {
  const backend = getBackendBase(env);
  if (!backend) {
    return json({ detail: "BACKEND_BASE_URL is not configured" }, 500);
  }

  const target = `${backend}${pathWithQuery}`;
  const method = request.method.toUpperCase();
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  const init = { method, headers };
  if (method !== "GET" && method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  let response;
  try {
    response = await fetch(target, init);
  } catch (error) {
    return json({ detail: `Backend fetch failed: ${String(error)}` }, 502);
  }

  const passthroughHeaders = new Headers();
  passthroughHeaders.set("content-type", response.headers.get("content-type") || "application/json; charset=utf-8");
  passthroughHeaders.set("cache-control", "no-store");
  return new Response(response.body, {
    status: response.status,
    headers: passthroughHeaders,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/") {
      return new Response(HTML, {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    if (url.pathname === "/health") {
      return json({ status: "ok", service: "cloudflare-ui" });
    }

    if (url.pathname === "/api/trial/live" && request.method === "POST") {
      return proxyToBackend(request, env, "/v1/trial/live");
    }

    if (url.pathname === "/api/trial/reset-state" && request.method === "POST") {
      return proxyToBackend(request, env, "/v1/trial/reset-state");
    }

    if (url.pathname === "/api/trial/summary" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/trial/summary${url.search}`);
    }

    if (url.pathname === "/api/review/queue" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/review/queue${url.search}`);
    }

    if (url.pathname.startsWith("/api/review/") && request.method === "POST") {
      const id = Number(url.pathname.replace("/api/review/", ""));
      if (!Number.isInteger(id) || id <= 0) {
        return json({ detail: "invalid opportunity id" }, 400);
      }
      return proxyToBackend(request, env, `/v1/review/${id}`);
    }

    if (url.pathname === "/api/analysis/reject-reasons" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/analysis/reject-reasons${url.search}`);
    }

    if (url.pathname === "/api/analysis/compliance-risks" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/analysis/compliance-risks${url.search}`);
    }

    if (url.pathname === "/api/analysis/api-usage" && request.method === "GET") {
      return proxyToBackend(request, env, "/v1/analysis/api-usage");
    }

    if (url.pathname === "/api/categories/suggestions" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/categories/suggestions${url.search}`);
    }

    if (url.pathname === "/api/system/thresholds" && request.method === "GET") {
      return proxyToBackend(request, env, `/v1/system/thresholds${url.search}`);
    }

    return json({ detail: "not found" }, 404);
  },
};
