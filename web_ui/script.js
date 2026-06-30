// ==============================================
// MLB 侍速報 — フロントエンド JavaScript
// Flask の /api/stats エンドポイントからデータを取得し、
// テーブルを動的に組み立てて表示します。
// ==============================================


/** 日付入力欄の初期化 */
function initDateInput() {
  const dateInput = document.getElementById("date-input");
  if (!dateInput) return;

  // 日本時間（UTC+9）の現在日時を基準にする
  const jstNow = new Date(Date.now() + 9 * 60 * 60 * 1000);
  
  // 最大値（今日）
  const maxYear = jstNow.getUTCFullYear();
  const maxMonth = String(jstNow.getUTCMonth() + 1).padStart(2, '0');
  const maxDate = String(jstNow.getUTCDate()).padStart(2, '0');
  dateInput.max = `${maxYear}-${maxMonth}-${maxDate}`;

  // 最小値（2026-01-01）
  dateInput.min = "2026-01-01";

  // 初期値（本日）
  const year = jstNow.getUTCFullYear();
  const month = String(jstNow.getUTCMonth() + 1).padStart(2, '0');
  const day = String(jstNow.getUTCDate()).padStart(2, '0');
  dateInput.value = `${year}-${month}-${day}`;
}

/** 表示エリアの表示/非表示を切り替えるヘルパー */
function show(id)  { document.getElementById(id).style.display = ""; }
function hide(id)  { document.getElementById(id).style.display = "none"; }
function clear(id) { document.getElementById(id).innerHTML = ""; }

/** ローディング開始 */
function startLoading() {
  hide("stats-section");
  hide("no-data");
  hide("error-box");
  show("loading");
  document.getElementById("refresh-btn").disabled = true;
}

/** ローディング終了 */
function stopLoading() {
  hide("loading");
  document.getElementById("refresh-btn").disabled = false;
}

/**
 * メイン：/api/stats を呼び出し、成績を描画する
 * ボタンの onclick から呼ばれます。
 */
async function loadStats() {
  startLoading();

  const dateInput = document.getElementById("date-input");
  let selectedDate = dateInput ? dateInput.value : "";
  if (!selectedDate) {
    const jstNow = new Date(Date.now() + 9 * 60 * 60 * 1000);
    const y = jstNow.getUTCFullYear();
    const m = String(jstNow.getUTCMonth() + 1).padStart(2, '0');
    const d = String(jstNow.getUTCDate()).padStart(2, '0');
    selectedDate = `${y}-${m}-${d}`;
  }
  
  // Flask API を呼び出してデータを取得（裏側で過去7日分も自動取得される）
  const url = `/api/stats?date=${selectedDate}`;

  try {
    const res = await fetch(url);

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const errMsg = errData.error ? errData.error : `サーバーエラー: HTTP ${res.status}`;
      throw new Error(errMsg);
    }

    const data = await res.json(); // APIからのレスポンスは { date, count, results: [...] } 形式
    stopLoading();

    const results = data.results || [];

    if (!results || results.length === 0) {
      const titleEl = document.querySelector("#no-data .no-data-title");
      if (titleEl) {
        titleEl.textContent = `${selectedDate} の試合データがありません`;
      }
      show("no-data");
      return;
    }

    renderStats(results);
    show("stats-section");

  } catch (err) {
    stopLoading();
    document.getElementById("error-message").textContent =
      `データの取得に失敗しました。まだ本日のデータが生成されていないか、日付が間違っています。（詳細: ${err.message}）`;
    show("error-box");
  }
}

/**
 * 成績データをテーブルに描画する
 * @param {Array} results - /api/stats の results 配列
 */
function renderStats(results) {
  // テーブルをリセット
  clear("batting-body");
  clear("pitching-body");

  let hasBatting  = false;
  let hasPitching = false;

  results.forEach((r) => {
    // --- 打撃成績 ---
    if (r.batting) {
      hasBatting = true;
      const b = r.batting;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="player-name">${r.player}</td>
        <td class="team-vs">${r.team_vs}</td>
        <td class="num today-stat">${b.AB}</td>
        <td class="num today-stat">${b.H}</td>
        <td class="num today-stat ${b.HR > 0 ? "highlight-hr" : ""}">${b.HR}</td>
        <td class="num today-stat">${b.RBI}</td>
        <td class="num today-stat">${b.BB}</td>
        <td class="num today-stat">${b.SO}</td>
        <td class="num season-stat">${b.season_avg || "-.---"}</td>
        <td class="num season-stat">${b.season_hr || "0"}</td>
        <td class="num season-stat">${b.season_rbi || "0"}</td>
      `;
      document.getElementById("batting-body").appendChild(tr);
    }

    // --- 投手成績 ---
    if (r.pitching) {
      hasPitching = true;
      const p = r.pitching;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="player-name">${r.player}</td>
        <td class="team-vs">${r.team_vs}</td>
        <td class="num today-stat">${p.IP}</td>
        <td class="num today-stat">${p.H}</td>
        <td class="num today-stat">${p.ER}</td>
        <td class="num today-stat">${p.BB}</td>
        <td class="num today-stat ${p.SO >= 6 ? "highlight-so" : ""}">${p.SO}</td>
        <td class="num today-stat">${p.ERA}</td>
        <td class="num season-stat">${p.season_wins || "0"}勝 ${p.season_losses || "0"}敗</td>
        <td class="num season-stat">${p.season_era || "-.--"}</td>
        <td class="num season-stat">${p.season_so || "0"}</td>
      `;
      document.getElementById("pitching-body").appendChild(tr);
    }
  });

  // セクションの表示/非表示
  document.getElementById("batting-section").style.display  = hasBatting  ? "" : "none";
  document.getElementById("pitching-section").style.display = hasPitching ? "" : "none";
}

// ページ読み込み時に実行
initDateInput();
loadStats();   // 起動時に自動取得
