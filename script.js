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
}

/** ローディング終了 */
function stopLoading() {
  hide("loading");
}

/**
 * メイン：/api/stats を呼び出し、成績を描画する
 * ボタンの onclick から呼ばれます。
 */
async function loadStats() {
  startLoading();

  const jstNow = new Date(Date.now() + 9 * 60 * 60 * 1000);
  const y = jstNow.getUTCFullYear();
  const m = String(jstNow.getUTCMonth() + 1).padStart(2, '0');
  const d = String(jstNow.getUTCDate()).padStart(2, '0');
  const todayStr = `${y}-${m}-${d}`;

  const dateInput = document.getElementById("date-input");
  let selectedDate = dateInput ? dateInput.value : "";
  if (!selectedDate) {
    selectedDate = todayStr;
  }
  
  // Netlify上の静的データファイル（JSON）を直接取得する
  const url = `./data/${selectedDate}_stats.json`;

  try {
    const res = await fetch(url);

    if (!res.ok) {
      if (res.status === 404) {
        throw new Error("この日付のデータはまだ準備されていません。");
      }
      throw new Error(`サーバーエラー: HTTP ${res.status}`);
    }

    const data = await res.json(); // 静的JSONは直接配列が返ってくる
    stopLoading();

    // 静的ファイルの場合は data 自体が配列。API形式に備えてフォールバックも残す
    const results = Array.isArray(data) ? data : (data.results || []);

    if (!results || results.length === 0) {
      if (selectedDate === todayStr) {
        throw new Error("本日分のデータはまだ生成されていません。");
      }
      const titleEl = document.querySelector("#no-data .no-data-title");
      if (titleEl) {
        titleEl.textContent = `${selectedDate} の試合データがありません`;
      }
      show("no-data");
      return;
    }

    renderStats(results, selectedDate, todayStr);
    show("stats-section");

  } catch (err) {
    stopLoading();
    if (selectedDate === todayStr) {
      const dayOfWeek = jstNow.getDay();
      let msg = "当日のデータは、午後1時30分と午後5時30分以降に順次反映されます。"; // 火〜土のデフォルト
      if (dayOfWeek === 0 || dayOfWeek === 1) { // 日曜日(0) または 月曜日(1)
        msg = "当日のデータは、午前11時30分と午後3時30分以降に順次反映されます。";
      }
      document.getElementById("error-message").textContent = msg;
    } else {
      document.getElementById("error-message").textContent =
        `データの取得に失敗しました。まだデータが生成されていないか、日付が間違っています。（詳細: ${err.message}）`;
    }
    show("error-box");
  }
}

/**
 * 成績データをテーブルに描画する
 * @param {Array} results - /api/stats の results 配列
 * @param {string} selectedDate - 表示対象の日付 (YYYY-MM-DD)
 * @param {string} todayStr - 今日の日付 (YYYY-MM-DD)
 */
function renderStats(results, selectedDate, todayStr) {
  // テーブルをリセット
  clear("batting-body");
  clear("pitching-body");

  // 過去の日付の場合、team_vs から「 (試合終了)」を取り除く
  const isPastDate = selectedDate && todayStr && selectedDate < todayStr;
  if (isPastDate) {
    results = results.map(r => ({
      ...r,
      team_vs: (r.team_vs || "").replace(" (試合終了)", "")
    }));
  }

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
