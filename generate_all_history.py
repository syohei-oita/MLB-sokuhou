# -*- coding: utf-8 -*-
"""
過去データ一括取得スクリプト
2026年MLB開幕日（3月25日）から本日まで、
まだファイルが存在しない日のデータをまとめて取得・保存します。
"""

import os
import time
from datetime import datetime, timedelta, timezone
from get_mlb_stats import fetch_stats_for_date, write_outputs

# =============================================
# 設定
# =============================================
START_DATE = "2026-03-25"   # MLB開幕日（日本時間表記）
WAIT_SECONDS = 0.5          # 1日分取得するごとの待ち時間（秒）

def main():
    # 日本時間の「今日」を取得
    jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = jst_time.strftime("%Y-%m-%d")

    # 開始日から今日までの日付リストを作成
    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime(today_str, "%Y-%m-%d")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui", "data")
    os.makedirs(output_dir, exist_ok=True)

    # 対象日数を計算
    total_days = (end_dt - start_dt).days + 1
    print(f"=== 一括データ取得開始 ===")
    print(f"対象期間: {START_DATE} ～ {today_str}（{total_days}日分）")
    print(f"既存ファイルはスキップします。")
    print("=" * 40)

    skipped = 0
    fetched = 0
    empty = 0
    errors = 0

    for i in range(total_days):
        current_dt = start_dt + timedelta(days=i)
        current_date_str = current_dt.strftime("%Y-%m-%d")

        json_path = os.path.join(output_dir, f"{current_date_str}_stats.json")

        # 既にファイルが存在する日はスキップ
        if os.path.exists(json_path):
            print(f"  [{i+1:3d}/{total_days}] {current_date_str} ... スキップ（既存）")
            skipped += 1
            continue

        print(f"  [{i+1:3d}/{total_days}] {current_date_str} ... 取得中...")

        try:
            results = fetch_stats_for_date(current_date_str)
            write_outputs(results, current_date_str)
            if results:
                print(f"    → {len(results)}名分のデータを保存しました。")
                fetched += 1
            else:
                print(f"    → 出場データなし（試合なし or 日本人選手不出場）")
                empty += 1
        except Exception as e:
            print(f"    → エラーが発生しました: {e}")
            errors += 1

        # API負荷対策のウェイト
        time.sleep(WAIT_SECONDS)

    print("\n" + "=" * 40)
    print("=== 一括データ取得完了 ===")
    print(f"  スキップ（既存）: {skipped}日")
    print(f"  新規取得（データあり）: {fetched}日")
    print(f"  新規取得（データなし）: {empty}日")
    print(f"  エラー: {errors}日")
    print("=" * 40)

if __name__ == "__main__":
    main()
