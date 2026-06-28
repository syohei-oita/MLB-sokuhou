# -*- coding: utf-8 -*-
"""
MLB日本人選手成績取得ツール
日本時間の「本日」の試合から日本人選手の成績を取得し、
コンソール出力・CSV/JSON保存を行います。
"""
import urllib.request
import json
import os
import csv
from datetime import datetime, timedelta, timezone

# =============================================
# 日本人選手の選手ID → 表示名の辞書
# =============================================
JAPANESE_PLAYERS = {
    660271: "大谷 翔平 (LAD)",
    673548: "鈴木 誠也 (CHC)",
    807799: "吉田 正尚 (BOS)",
    684007: "今永 昇太 (CHC)",
    808967: "山本 由伸 (LAD)",
    506433: "ダルビッシュ 有 (SD)",
    606205: "松井 裕樹 (SD)",
    579328: "菊池 雄星 (HOU)",
    673540: "千賀 滉大 (NYM)",
    699661: "菅野 智之 (COL)",
    703498: "佐々木 朗希 (LAD)",
    837227: "今井 達也 (HOU)",
    672960: "岡本 和真 (TOR)",
    808959: "村上 宗隆 (CWS)",
}


def get_json(url):
    """指定URLからJSONを取得して返す。失敗時はNoneを返す。"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def fetch_stats_for_date(target_date):
    """
    指定日（YYYY-MM-DD、日本時間表記）の全試合を走査し、
    日本人選手の成績をリスト形式で返す。
    内部では、指定日の前日（米国時間）のデータを取得します。
    戻り値: [{ date, player, team_vs, batting?, pitching? }, ...]
    """
    # 日本時間の日付から1日引いて、米国時間（APIに渡す日付）を計算する
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        us_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
    except ValueError:
        us_date = target_date

    schedule_url = (
        f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={us_date}"
    )
    schedule_data = get_json(schedule_url)
    if (
        not schedule_data
        or "dates" not in schedule_data
        or not schedule_data["dates"]
    ):
        return []

    games = schedule_data["dates"][0].get("games", [])
    results = []

    for game in games:
        game_pk = game.get("gamePk")
        teams = game.get("teams", {})
        away_team = teams.get("away", {}).get("team", {}).get("name", "Unknown")
        home_team = teams.get("home", {}).get("team", {}).get("name", "Unknown")

        boxscore = get_json(
            f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        )
        if not boxscore:
            continue

        for team_type in ["away", "home"]:
            team_players = (
                boxscore.get("teams", {}).get(team_type, {}).get("players", {})
            )
            for player_data in team_players.values():
                player_id = player_data.get("person", {}).get("id")
                if player_id not in JAPANESE_PLAYERS:
                    continue

                stats = player_data.get("stats", {})
                batting = stats.get("batting", {})
                pitching = stats.get("pitching", {})

                has_batted = (
                    batting.get("atBats", 0) > 0
                    or batting.get("plateAppearances", 0) > 0
                )
                has_pitched = pitching.get("inningsPitched", "0.0") != "0.0"

                if not (has_batted or has_pitched):
                    continue

                result = {
                    "date": target_date,
                    "player": JAPANESE_PLAYERS[player_id],
                    "team_vs": f"{away_team} vs {home_team}",
                }
                if has_batted:
                    season_batting = player_data.get("seasonStats", {}).get("batting", {})
                    result["batting"] = {
                        "AB":  batting.get("atBats", 0),
                        "H":   batting.get("hits", 0),
                        "HR":  batting.get("homeRuns", 0),
                        "RBI": batting.get("rbi", 0),
                        "BB":  batting.get("baseOnBalls", 0),
                        "SO":  batting.get("strikeOuts", 0),
                        "season_avg": season_batting.get("avg", "-.---"),
                        "season_hr": season_batting.get("homeRuns", 0),
                        "season_rbi": season_batting.get("rbi", 0),
                    }
                if has_pitched:
                    season_pitching = player_data.get("seasonStats", {}).get("pitching", {})
                    result["pitching"] = {
                        "IP":  pitching.get("inningsPitched", "0.0"),
                        "H":   pitching.get("hits", 0),
                        "ER":  pitching.get("earnedRuns", 0),
                        "BB":  pitching.get("baseOnBalls", 0),
                        "SO":  pitching.get("strikeOuts", 0),
                        "ERA": pitching.get("era", "-.--"),
                        "season_wins": season_pitching.get("wins", 0),
                        "season_losses": season_pitching.get("losses", 0),
                        "season_era": season_pitching.get("era", "-.--"),
                        "season_so": season_pitching.get("strikeOuts", 0),
                    }
                results.append(result)

    return results


def write_outputs(results, date_str):
    """
    成績リストを CSV と JSON に書き出す。
    出力先: スクリプトと同フォルダの web_ui/data/ ディレクトリ
    """
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui", "data")
    os.makedirs(output_dir, exist_ok=True)

    csv_path  = os.path.join(output_dir, f"{date_str}_stats.csv")
    json_path = os.path.join(output_dir, f"{date_str}_stats.json")

    # --- CSV ---
    csv_fields = [
        "date", "player", "team_vs",
        "AB", "H", "HR", "RBI", "BB", "SO", "season_avg", "season_hr", "season_rbi", # 打撃
        "IP", "ER", "BB_pitch", "SO_pitch", "ERA", "season_wins", "season_losses", "season_era", "season_so" # 投手
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in results:
            writer.writerow({
                "date":          r.get("date", ""),
                "player":        r.get("player", ""),
                "team_vs":       r.get("team_vs", ""),
                "AB":            r.get("batting", {}).get("AB", ""),
                "H":             r.get("batting", {}).get("H", ""),
                "HR":            r.get("batting", {}).get("HR", ""),
                "RBI":           r.get("batting", {}).get("RBI", ""),
                "BB":            r.get("batting", {}).get("BB", ""),
                "SO":            r.get("batting", {}).get("SO", ""),
                "season_avg":    r.get("batting", {}).get("season_avg", ""),
                "season_hr":     r.get("batting", {}).get("season_hr", ""),
                "season_rbi":    r.get("batting", {}).get("season_rbi", ""),
                "IP":            r.get("pitching", {}).get("IP", ""),
                "ER":            r.get("pitching", {}).get("ER", ""),
                "BB_pitch":      r.get("pitching", {}).get("BB", ""),
                "SO_pitch":      r.get("pitching", {}).get("SO", ""),
                "ERA":           r.get("pitching", {}).get("ERA", ""),
                "season_wins":   r.get("pitching", {}).get("season_wins", ""),
                "season_losses": r.get("pitching", {}).get("season_losses", ""),
                "season_era":    r.get("pitching", {}).get("season_era", ""),
                "season_so":     r.get("pitching", {}).get("season_so", ""),
            })

    # --- JSON ---
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 ファイルを保存しました：")
    print(f"   CSV  → {csv_path}")
    print(f"   JSON → {json_path}")
    print("\nヒント: Webサイト用のデータフォルダ (web_ui/data/) に保存しました。")
    print("        これらは自動的にウェブサイトへ公開されます。")

    return {"csv": csv_path, "json": json_path}


def main():
    """メインエントリーポイント（コマンドライン実行用）"""
    # 日本時間（UTC+9）の「本日」を取得する
    jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = jst_time.strftime("%Y-%m-%d")
    print(f"=== MLB 日本人選手成績速報（日本日付: {today_str}）===")

    results = fetch_stats_for_date(today_str)

    if not results:
        print("\n本日、出場した日本人選手は検出されませんでした。")
        return

    for r in results:
        print(f"\n🔵 選手名: {r['player']}")
        print(f"   対戦カード: {r['team_vs']}")
        if "batting" in r:
            b = r["batting"]
            print(
                f"   【打撃】 {b['AB']}打数 {b['H']}安打 {b['HR']}本塁打"
                f" {b['RBI']}打点（四球:{b['BB']} 三振:{b['SO']}）"
            )
        if "pitching" in r:
            p = r["pitching"]
            print(
                f"   【投手】 {p['IP']}回 被安打{p['H']} 自責点{p['ER']}"
                f" 四球{p['BB']} 奪三振{p['SO']}（防御率: {p['ERA']}）"
            )

    write_outputs(results, today_str)


if __name__ == "__main__":
    main()
