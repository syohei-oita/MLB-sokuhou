# MLB 日本人選手成績速報ツール

本日（日本時間）のメジャーリーグで活躍した日本人選手の成績を取得し、
**ブラウザでの確認**・**CSV/JSON 保存**ができるツールです。

---

## 📁 ファイル構成

```
MLB sokuhou/
├── get_mlb_stats.py   ← 成績取得の本体スクリプト
├── app.py             ← Web UI 用 Flask サーバ
├── requirements.txt   ← 必要なライブラリ一覧
├── output/            ← CSV・JSON の保存先（自動作成）
│   └── YYYYMMDD_stats.csv / .json
└── web_ui/            ← ブラウザ UI のファイル
    ├── index.html
    ├── style.css
    └── script.js
```

---

## 🚀 初回セットアップ（一度だけ実施）

PowerShell（または コマンドプロンプト）を開き、以下のコマンドを実行してください。

```powershell
cd "c:\Users\pc\OneDrive\画像\2026 Antigravity\MLB sokuhou"
pip install -r requirements.txt
```

---

## 💻 使い方 A：コマンドラインで実行（シンプル版）

```powershell
python get_mlb_stats.py
```

- コンソールに成績が表示されます。
- `output/YYYYMMDD_stats.csv` と `output/YYYYMMDD_stats.json` に自動保存されます。

**CSV を Excel で開くには**  
① `output` フォルダ内の `.csv` ファイルを右クリック  
② 「プログラムから開く」→「Excel」を選択

**メールに添付するには**  
① `output` フォルダ内の `.csv` or `.json` ファイルのパスをコピー  
② Outlook や Gmail に添付ファイルとしてドラッグ＆ドロップ

---

## 🌐 使い方 B：ブラウザで確認（Web UI 版）

### 1. Flask サーバを起動

```powershell
python app.py
```

以下のようなメッセージが出ます：

```
==================================================
  MLB 日本人選手成績 Web UI サーバを起動します
  ブラウザで http://localhost:5000 を開いてください
==================================================
```

### 2. ブラウザでアクセス

Edge または Chrome で `http://localhost:5000` を開いてください。

### 3. 成績を取得

「🔄 成績を取得」ボタンを押すと本日の成績が表示されます。  
同時に `output/` フォルダに CSV と JSON も自動保存されます。

### 4. サーバを終了

PowerShell 上で `Ctrl + C` を押してください。

---

## 👥 登録済み日本人選手

| 選手名 | 球団 |
|--------|------|
| 大谷 翔平 | ロサンゼルス・ドジャース (LAD) |
| 山本 由伸 | ロサンゼルス・ドジャース (LAD) |
| 鈴木 誠也 | シカゴ・カブス (CHC) |
| 今永 昇太 | シカゴ・カブス (CHC) |
| 吉田 正尚 | ボストン・レッドソックス (BOS) |
| ダルビッシュ 有 | サンディエゴ・パドレス (SD) |
| 松井 裕樹 | サンディエゴ・パドレス (SD) |
| 菊池 雄星 | ヒューストン・アストロズ (HOU) |
| 千賀 滉大 | ニューヨーク・メッツ (NYM) |
| ラーズ・ヌートバー | セントルイス・カージナルス (STL) |

---

## ❓ よくある質問

**Q: データが取得できない / 「選手が検出されませんでした」と表示される**  
A: 日本時間の当日にまだ試合が行われていない可能性があります。  
　 MLB の試合は通常、日本時間の午前〜午後に終了するため、夜以降にお試しください。

**Q: Flask サーバが起動しない**  
A: `pip install flask` を再度試してください。

---

*データ提供: MLB Stats API (statsapi.mlb.com)*
