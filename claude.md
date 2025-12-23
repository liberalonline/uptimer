# Discord Ubuntu Server Monitor Bot

## 概要
UbuntuマシンのシステムリソースとアップタイムをDiscordで表示するPython製監視ボット

## 主な機能

### 1. システム情報の監視と表示
各ホストごとに1つのDiscord埋め込み（Embed）メッセージを作成し、以下の情報を表示:

- **ローカルマシン監視**: ボット自身が動作しているマシンの情報を自動で表示（psutil使用）
- **ホスト名とIPアドレス**: サーバーの識別情報
- **CPU情報**: モデル名と使用率
- **メモリ情報**: 総容量と使用量
- **ディスク情報**: 総容量と使用率
- **プロセス数とロードアベレージ**: システム負荷
- **アップタイム**: 過去48時間の稼働状況を視覚的に表示
  - 🟩: 稼働中（1時間単位）
  - 🟥: ダウン時間（1時間単位）
  - 計48個の絵文字で48時間分を表示

### 2. 複数ホスト監視の実装方法

#### ローカルマシンの監視
- ボットが動作しているマシンの情報を`psutil`で直接取得
- SSH接続不要で効率的
- 常に監視対象（設定不要）

#### リモートホストの監視（SSH経由）
- 1台のマシンから他のホストにSSH接続
- リモートでコマンド実行して情報を取得
- メリット: 各ホストにボットを配置する必要がない
- デメリット: SSH認証の管理が必要
- hosts.jsonで設定（オプション）

## 技術仕様

### 使用ライブラリ
- `discord.py`: Discord APIクライアント
- `psutil`: システム情報取得
- `python-dotenv`: 環境変数管理
- `paramiko`: SSH接続
- `sqlite3`: アップタイム履歴の保存

### コマンド例
- `/status` or `!status`: 全監視対象ホストのステータス表示
- `/status <hostname>`: 特定ホストのステータス表示
- `/uptime`: アップタイム情報のみ表示

### 埋め込みメッセージの構造
```
┌─────────────────────────────────────────┐
│ host: `ubuntu-server-01`                │
│ ip: `192.168.1.1`                       │
├─────────────────────────────────────────┤
│ リソース              │ 使用率          │
│ 📊 CPU: `Xeon E5-xxxx`│ `25.1%`        │
│ 💾 RAM: `16GB`        │ `8.5GB`        │
│ 💿 Disk: `500GB`      │ `35%`          │
│ 🔄 Process: `178`     │ Load Avg: `1.4`│
├─────────────────────────────────────────┤
│ Uptime (48h):                           │
│ 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟥🟥🟥... │
│ (48個の絵文字で48時間分の稼働状況)      │
└─────────────────────────────────────────┘
```

**アップタイム表示の仕様:**
- 🟩: 稼働中（1時間）
- 🟥: ダウン状態（1時間）
- 総計48個の絵文字で過去48時間を表示
- 1時間ごとに左から右へ進行
- 古いデータは左端から消え、新しいデータが右端に追加される

### 更新頻度
- 定期的な自動更新（例: 60秒ごと）
- メッセージの編集による更新（新規投稿を避ける）

## 実装方針

### ファイル構成

```
dcmt/
├── bot.py              # メインのボットロジック
├── monitor.py          # システム情報取得（SSH経由）
├── ssh_client.py       # SSH接続管理
├── uptime_tracker.py   # アップタイム履歴管理
├── config.py           # 設定管理
├── hosts.json          # 監視対象ホストの設定
├── uptime_history.db   # アップタイム履歴データベース
├── .env               # トークンなどの環境変数
├── .gitignore         # Git除外設定
└── requirements.txt   # 依存パッケージ
```

### 環境変数
- `DISCORD_TOKEN`: Discordボットのトークン
- `CHANNEL_ID`: 監視情報を投稿するチャンネルID
- `UPDATE_INTERVAL`: 更新間隔（秒、デフォルト: 60）
- `UPTIME_CHECK_INTERVAL`: アップタイム記録間隔（秒、デフォルト: 3600 = 1時間）

### hosts.json の構造例

**公開鍵認証の場合:**
```json
{
  "hosts": [
    {
      "name": "ubuntu-server-01",
      "ip": "192.168.1.10",
      "ssh_port": 22,
      "ssh_user": "monitor",
      "ssh_key_path": "~/.ssh/id_rsa"
    }
  ]
}
```

**パスワード認証の場合:**
```json
{
  "hosts": [
    {
      "name": "ubuntu-server-02",
      "ip": "192.168.1.11",
      "ssh_port": 22,
      "ssh_user": "monitor",
      "ssh_password": "your_password_here"
    }
  ]
}
```

**注意:**
- `ssh_key_path`または`ssh_password`のいずれか一方を指定
- パスワード認証は平文保存のためセキュリティリスクあり
- 公開鍵認証の使用を推奨

### 取得する情報とコマンド
- **CPU モデル**: `cat /proc/cpuinfo | grep "model name" | head -1`
- **CPU 使用率**: `top -bn1 | grep "Cpu(s)" | awk '{print $2}'`
- **メモリ総容量**: `free -h | grep Mem | awk '{print $2}'`
- **メモリ使用量**: `free -h | grep Mem | awk '{print $3}'`
- **ディスク総容量**: `df -h / | tail -1 | awk '{print $2}'`
- **ディスク使用率**: `df -h / | tail -1 | awk '{print $5}'`
- **プロセス数**: `ps aux | wc -l`
- **ロードアベレージ**: `uptime | awk -F'load average:' '{print $2}' | awk '{print $1}'`

## セキュリティ
- トークンは環境変数で管理
- `.env`ファイルは`.gitignore`に追加
- 必要最小限の権限でボットを動作

## データ保存形式

### uptime_history.db (SQLite)
```sql
CREATE TABLE uptime_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL,
    timestamp INTEGER NOT NULL,  -- UNIX timestamp
    status INTEGER NOT NULL,      -- 1: 稼働, 0: ダウン
    UNIQUE(hostname, timestamp)
);

CREATE INDEX idx_hostname_timestamp ON uptime_history(hostname, timestamp);
```

### アップタイム履歴の管理ロジック
1. 1時間ごとにホストに接続を試行
2. 接続成功 → status=1、接続失敗 → status=0 をDBに記録
3. 表示時は過去48時間分（48レコード）を取得
4. 古いデータは自動的に削除（48時間以上前のレコード）

## 拡張機能（将来的に）
- アラート機能（使用率が閾値を超えた場合に通知）
- 履歴グラフの表示
- ネットワークトラフィック監視
- カスタム監視項目の追加
- Webhook対応（他システムからの通知）
