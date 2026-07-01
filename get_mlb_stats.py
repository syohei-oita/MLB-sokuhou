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
import concurrent.futures
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

# =============================================
# 球団名（英語 → カタカナ）の変換辞書
# =============================================
TEAM_TRANSLATIONS = {
    # AL East
    "Baltimore Orioles": "オリオールズ",
    "Orioles": "オリオールズ",
    "Boston Red Sox": "レッドソックス",
    "Red Sox": "レッドソックス",
    "New York Yankees": "ヤンキース",
    "Yankees": "ヤンキース",
    "Tampa Bay Rays": "レイズ",
    "Rays": "レイズ",
    "Toronto Blue Jays": "ブルージェイズ",
    "Blue Jays": "ブルージェイズ",

    # AL Central
    "Chicago White Sox": "ホワイトソックス",
    "White Sox": "ホワイトソックス",
    "Cleveland Guardians": "ガーディアンズ",
    "Guardians": "ガーディアンズ",
    "Detroit Tigers": "タイガース",
    "Tigers": "タイガース",
    "Minnesota Twins": "ツインズ",
    "Twins": "ツインズ",
    "Kansas City Royals": "ロイヤルズ",
    "Royals": "ロイヤルズ",

    # AL West
    "Houston Astros": "アストロズ",
    "Astros": "アストロズ",
    "Los Angeles Angels": "エンゼルス",
    "Angels": "エンゼルス",
    "Oakland Athletics": "アスレチックス",
    "Athletics": "アスレチックス",
    "Oakland A's": "アスレチックス",
    "Seattle Mariners": "マリナーズ",
    "Mariners": "マリナーズ",
    "Texas Rangers": "レンジャーズ",
    "Rangers": "レンジャーズ",

    # NL East
    "Philadelphia Phillies": "フィリーズ",
    "Phillies": "フィリーズ",
    "Atlanta Braves": "ブレーブス",
    "Braves": "ブレーブス",
    "Miami Marlins": "マーリンズ",
    "Marlins": "マーリンズ",
    "Washington Nationals": "ナショナルズ",
    "Nationals": "ナショナルズ",
    "New York Mets": "メッツ",
    "Mets": "メッツ",

    # NL Central
    "Milwaukee Brewers": "ブルワーズ",
    "Brewers": "ブルワーズ",
    "St. Louis Cardinals": "カージナルス",
    "Cardinals": "カージナルス",
    "Cincinnati Reds": "レッズ",
    "Reds": "レッズ",
    "Pittsburgh Pirates": "パイレーツ",
    "Pirates": "パイレーツ",
    "Chicago Cubs": "カブス",
    "Cubs": "カブス",

    # NL West
    "San Francisco Giants": "ジャイアンツ",
    "Giants": "ジャイアンツ",
    "Colorado Rockies": "ロッキーズ",
    "Rockies": "ロッキーズ",
    "Los Angeles Dodgers": "ドジャース",
    "Dodgers": "ドジャース",
    "San Diego Padres": "パドレス",
    "Padres": "パドレス",
    "Arizona Diamondbacks": "ダイヤモンドバックス",
    "Diamondbacks": "ダイヤモンドバックス",
    "D-backs": "ダイヤモンドバックス"
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

    # 今日（日本時間）かどうかを判定しておく
    jst_today_str = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")
    is_today = (target_date == jst_today_str)

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

    def process_game(game):
        game_results = []
        game_pk = game.get("gamePk")
        teams = game.get("teams", {})
        away_info = teams.get("away", {})
        home_info = teams.get("home", {})
        away_team_en = away_info.get("team", {}).get("name", "Unknown")
        home_team_en = home_info.get("team", {}).get("name", "Unknown")
        away_team = TEAM_TRANSLATIONS.get(away_team_en, away_team_en)
        home_team = TEAM_TRANSLATIONS.get(home_team_en, home_team_en)
        
        away_score = away_info.get("score")
        home_score = home_info.get("score")
        detailed_state = game.get("status", {}).get("detailedState", "")
        
        if away_score is not None and home_score is not None:
            team_vs_display = f"{away_team} {away_score} - {home_score} {home_team}"
        else:
            team_vs_display = f"{away_team} vs {home_team}"
            
        if detailed_state in ["Final", "Completed Early", "Game Over"]:
            if is_today:
                team_vs_display += " (試合終了)"
        elif detailed_state == "In Progress":
            team_vs_display += " (試合中)"
        elif detailed_state == "Postponed":
            team_vs_display += " (延期)"
        elif detailed_state in ["Scheduled", "Pre-Game", "Warmup"]:
            team_vs_display += " (試合前)"

        boxscore = get_json(
            f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        )
        if not boxscore:
            return game_results

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
                    "team_vs": team_vs_display,
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
                game_results.append(result)
        return game_results

    # 15試合程度のデータを並列で取得する（最大15スレッド）
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(process_game, game) for game in games]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                results.extend(res)

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

    print(f"\n[保存] ファイルを保存しました：")
    print(f"   CSV  : {csv_path}")
    print(f"   JSON : {json_path}")
    print("\nヒント: Webサイト用のデータフォルダ (web_ui/data/) に保存しました。")
    print("        これらは自動的にウェブサイトへ公開されます。")

    return {"csv": csv_path, "json": json_path}


def fetch_and_save_past_days(target_date_str, days=2):
    """
    指定日を含め、過去 `days` 日分のデータを自動取得し、保存する。
    すでにその日のファイル(JSON)が存在し、かつデータが確定している（または直前に更新された）場合は取得をスキップする。
    戻り値: 指定日(target_date_str)の成績データ (リスト)
    """
    try:
        target_dt = datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        return []

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui", "data")

    # 日本時間の「今日」を取得
    jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = jst_time.strftime("%Y-%m-%d")

    for i in range(days):
        current_dt = target_dt - timedelta(days=i)
        current_date_str = current_dt.strftime("%Y-%m-%d")
        
        json_path = os.path.join(output_dir, f"{current_date_str}_stats.json")
        
        # すでにJSONファイルが存在する場合のスキップ判定
        if os.path.exists(json_path):
            # 1. 過去の日付（昨日以前）であれば、データは変わらないので常にスキップ
            if current_date_str < today_str:
                continue
                
            # 2. 今日の日付の場合、短時間キャッシュ（例: 5分）を適用
            if current_date_str == today_str:
                file_mtime = os.path.getmtime(json_path)
                elapsed_time = datetime.now().timestamp() - file_mtime
                if elapsed_time < 300:  # 5分以内
                    print(f"[{current_date_str}] は最近更新されたため、キャッシュを使用します。")
                    continue

        # 3. キャッシュ切れ、またはファイルが存在しない、または本日分で5分以上経過している場合
        # schedule API を1回叩いて、試合状況を確認する
        try:
            dt = datetime.strptime(current_date_str, "%Y-%m-%d")
            us_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            us_date = current_date_str

        schedule_url = f"https://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&date={us_date}"
        schedule_data = get_json(schedule_url)
        
        is_final = True
        if schedule_data and "dates" in schedule_data and schedule_data["dates"]:
            games = schedule_data["dates"][0].get("games", [])
            for game in games:
                status = game.get("status", {})
                abstract_state = status.get("abstractGameState", "")
                detailed_state = status.get("detailedState", "")
                if abstract_state in ["Preview", "Live"] or detailed_state in ["Scheduled", "Pre-Game", "Warmup", "In Progress"]:
                    is_final = False
                    break
        
        # すべての試合が終了しており、かつローカルにすでにJSONが存在するなら、APIからboxscoreを取得するのをスキップする
        if is_final and os.path.exists(json_path):
            print(f"[{current_date_str}] の試合はすべて終了しています。既存のデータを使用します。")
            try:
                os.utime(json_path, None) # mtimeを更新してキャッシュ時間を延ばす
            except Exception:
                pass
            continue

        # それ以外の場合は API から詳細データを取得
        print(f"[{current_date_str}] の成績データを自動取得しています...")
        results = fetch_stats_for_date(current_date_str)
        if results:
            write_outputs(results, current_date_str)
        else:
            if is_final:
                write_outputs([], current_date_str)

    # ターゲット日(target_date_str)のJSONファイルを読み込んで返す
    target_json_path = os.path.join(output_dir, f"{target_date_str}_stats.json")
    if os.path.exists(target_json_path):
        try:
            with open(target_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"ファイルの読み込みに失敗しました: {e}")
            
    return []


def main():
    """メインエントリーポイント（コマンドライン実行用）"""
    import sys

    # コマンドライン引数から日付を取得（指定がなければ日本時間の今日）
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        print(f"=== MLB 日本人選手成績速報（指定日付: {target_date}）===")
    else:
        # 日本時間（UTC+9）の「本日」を取得する
        jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
        target_date = jst_time.strftime("%Y-%m-%d")
        print(f"=== MLB 日本人選手成績速報（日本日付: {target_date}）===")

    results = fetch_stats_for_date(target_date)

    if not results:
        print(f"\n{target_date} に出場した日本人選手は検出されませんでした。")
        write_outputs([], target_date)
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

    write_outputs(results, target_date)


if __name__ == "__main__":
    main()
