# -*- coding: utf-8 -*-
"""
MLB日本人選手成績 Web UI サーバ
起動コマンド: python app.py
アクセス先: http://localhost:5000
"""
import os
import sys
from flask import Flask, jsonify, send_from_directory
from datetime import datetime, timedelta, timezone

# get_mlb_stats.py と同じフォルダを Python パスに追加
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from get_mlb_stats import fetch_stats_for_date, write_outputs, fetch_and_save_past_days

app = Flask(__name__, static_folder="web_ui", static_url_path="")


@app.route("/")
def index():
    """Web UI のトップページを返す"""
    return send_from_directory("web_ui", "index.html")


@app.route("/api/stats")
def get_stats():
    """
    指定日または本日（日本時間）の日本人選手成績を JSON で返す。
    フロントエンドの JavaScript がこのエンドポイントを呼び出す。
    """
    from flask import request
    
    # ユーザーが指定した日付を取得。無ければ「本日（日本時間）」をデフォルトにする
    date_str = request.args.get("date")
    jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = jst_time.strftime("%Y-%m-%d")
    
    if not date_str:
        date_str = today_str
        
    # 制限: 2026-01-01 より古い日付はエラーにする
    if date_str < "2026-01-01":
        return jsonify({"error": "2026年1月1日より前のデータは取得できません"}), 400

    # 指定日を含む過去2日分を自動取得（すでにある場合はスキップされる）
    results = fetch_and_save_past_days(date_str, days=2)

    # 昨日以前（過去）のデータの場合、「 (試合終了)」という文字列を削除
    if date_str < today_str:
        for r in results:
            if "team_vs" in r:
                r["team_vs"] = r["team_vs"].replace(" (試合終了)", "")

    return jsonify({
        "date": date_str,
        "count": len(results),
        "results": results
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  MLB 日本人選手成績 Web UI サーバを起動します")
    print("  ブラウザで http://localhost:5000 を開いてください")
    print("=" * 50)
    app.run(debug=True, host="127.0.0.1", port=5000)
