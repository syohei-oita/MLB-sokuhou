# -*- coding: utf-8 -*-
"""
MLB日本人選手成績メール送信スクリプト
本日の成績データを取得し、CSVファイルを添付して指定のアドレスにメールを送信します。
"""
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta, timezone

# 成績取得ロジックのインポート
import get_mlb_stats

def load_settings():
    """メール送信設定をロードする。環境変数を最優先し、無ければ config_email.json から読み込む"""
    settings = {
        "EMAIL_SENDER": os.environ.get("EMAIL_SENDER"),
        "EMAIL_PASSWORD": os.environ.get("EMAIL_PASSWORD"),
        "EMAIL_RECEIVER": os.environ.get("EMAIL_RECEIVER"),
        "SMTP_SERVER": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "SMTP_PORT": os.environ.get("SMTP_PORT", "587"),
    }
    
    # 環境変数が設定されていない項目がある場合、config_email.json から補完する
    if not settings["EMAIL_SENDER"] or not settings["EMAIL_PASSWORD"] or not settings["EMAIL_RECEIVER"]:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_email.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    for key in ["EMAIL_SENDER", "EMAIL_PASSWORD", "EMAIL_RECEIVER", "SMTP_SERVER", "SMTP_PORT"]:
                        if key in config and config[key]:
                            settings[key] = config[key]
            except Exception as e:
                print(f"警告: config_email.json の読み込み中にエラーが発生しました: {e}")
                
    return settings

def create_email_body(results, date_str):
    """取得結果からメール本文（テキスト）を作成する"""
    body = []
    body.append(f"=== MLB 日本人選手成績速報（日本日付: {date_str}）===\n")
    
    if not results:
        body.append("本日、試合に出場した日本人選手は検出されませんでした。")
        body.append("\n※日本時間の日付において、まだ試合が開始されていないか、本日は試合が無い可能性があります。")
        return "\n".join(body)
        
    for r in results:
        body.append(f"🔵 選手名: {r['player']}")
        body.append(f"   対戦カード: {r['team_vs']}")
        if "batting" in r:
            b = r["batting"]
            body.append(
                f"   【打撃】 {b['AB']}打数 {b['H']}安打 {b['HR']}本塁打"
                f" {b['RBI']}打点（四球:{b['BB']} 三振:{b['SO']}）\n"
                f"            今季通算: 率.{b['season_avg']}  {b['season_hr']}本塁打  {b['season_rbi']}打点"
            )
        if "pitching" in r:
            p = r["pitching"]
            body.append(
                f"   【投手】 {p['IP']}回 被安打{p['H']} 自責点{p['ER']}"
                f" 四球{p['BB']} 奪三振{p['SO']}（防御率: {p['ERA']}）\n"
                f"            今季通算: {p['season_wins']}勝{p['season_losses']}敗  防御率{p['season_era']}  {p['season_so']}奪三振"
            )
        body.append("-" * 45)
        
    body.append("\n※本日の詳細成績CSVファイルを添付しています。Excel等で開いてご確認ください。")
    body.append("※このメールは自動送信システム（GitHub Actions）から送信されています。")
    return "\n".join(body)

def send_email(settings, subject, body, attachment_path=None):
    """SMTPサーバーを利用してメールを送信する"""
    sender = settings["EMAIL_SENDER"]
    password = settings["EMAIL_PASSWORD"]
    receiver = settings["EMAIL_RECEIVER"]
    smtp_server = settings["SMTP_SERVER"]
    
    try:
        smtp_port = int(settings["SMTP_PORT"])
    except ValueError:
        smtp_port = 587
        
    if not sender or not password or not receiver:
        missing = []
        if not sender: missing.append("送信元アドレス(EMAIL_SENDER)")
        if not password: missing.append("アプリパスワード(EMAIL_PASSWORD)")
        if not receiver: missing.append("送信先アドレス(EMAIL_RECEIVER)")
        raise ValueError(f"以下の必須設定が不足しています: {', '.join(missing)}")
        
    # MIMEオブジェクトの作成
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    
    # メールの本文を設定
    msg.attach(MIMEText(body, "plain", "utf-8"))
    
    # 添付ファイルの設定
    if attachment_path and os.path.exists(attachment_path):
        filename = os.path.basename(attachment_path)
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            # 日本語ファイル名が文字化けしないよう適切にヘッダー設定
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={filename}",
            )
            msg.attach(part)
        except Exception as e:
            print(f"警告: 添付ファイルの処理中にエラーが発生しました: {e}")

    # SMTPサーバーに接続してメール送信
    print(f"SMTPサーバー ({smtp_server}:{smtp_port}) に接続中...")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # TLS暗号化通信の開始
        server.login(sender, password)
        server.send_message(msg)
        print("メールが正常に送信されました！")

def main():
    # 日本時間（UTC+9）の「本日」の日付を計算
    jst_time = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = jst_time.strftime("%Y-%m-%d")
    
    print(f"=== MLBメール自動送信処理を開始します（日本日付: {today_str}）===")
    
    # 1. 成績データの取得
    results = get_mlb_stats.fetch_stats_for_date(today_str)
    
    # 2. ローカルでのファイル保存（CSV・JSON）
    paths = get_mlb_stats.write_outputs(results, today_str)
    csv_path = paths.get("csv")
    
    # 3. メール本文の組み立て
    email_body = create_email_body(results, today_str)
    subject = f"【MLB成績速報】{today_str}"
    
    # 4. メール設定のロード
    settings = load_settings()
    
    # 5. メール送信の実行
    try:
        send_email(settings, subject, email_body, csv_path)
    except Exception as e:
        print(f"\n[エラー] メール送信に失敗しました:")
        print(e)
        print("\n■ 対処方法:")
        print("1. config_email.json（または環境変数）の設定値が正しいか確認してください。")
        print("2. 送信元アドレスがGmailの場合、Googleアカウントで『アプリパスワード』が正しく生成されているか確認してください。")

if __name__ == "__main__":
    main()
