# Discord Ubuntu Server Monitor Bot

UbuntuサーバーのシステムリソースとアップタイムをDiscordで監視・表示するPython製ボット

## 機能

- **ローカルマシン監視**: ボット自身が動作しているマシンの情報を自動で表示
- 複数のUbuntuサーバーをSSH経由で監視
- CPU、メモリ、ディスク使用率をリアルタイム表示
- 過去48時間のアップタイム履歴を視覚化（🟩🟥の絵文字で表示）
- 自動更新機能（デフォルト60秒間隔）
- Discordコマンドによる手動確認

## 必要要件

- Python 3.8以上
- Discordボット（Bot Token必須）
- 監視対象サーバーへのSSHアクセス（公開鍵認証）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`を作成:

```bash
cp .env.example .env
```

`.env`ファイルを編集して必要な値を設定:

```env
DISCORD_TOKEN=your_discord_bot_token_here
CHANNEL_ID=your_channel_id_here
UPDATE_INTERVAL=60
UPTIME_CHECK_INTERVAL=3600
```

### 3. 監視対象ホストの設定

`hosts.json`を編集して監視対象サーバーを追加（オプション）:

**注意:** ボット自身が動作しているローカルマシンは常に監視されます。リモートサーバーを監視しない場合は、`hosts.json`を空のままでも構いません。

```json
{
  "hosts": []
}
```

**公開鍵認証を使用する場合:**
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

**パスワード認証を使用する場合:**
```json
{
  "hosts": [
    {
      "name": "ubuntu-server-01",
      "ip": "192.168.1.10",
      "ssh_port": 22,
      "ssh_user": "monitor",
      "ssh_password": "your_password_here"
    }
  ]
}
```

**注意:** パスワードを平文で保存するため、セキュリティ上は公開鍵認証の使用を推奨します。

### 4. SSH認証の設定

#### 公開鍵認証（推奨）

監視対象サーバーに公開鍵認証でSSH接続できるようにしてください:

```bash
# SSH鍵の生成（まだ持っていない場合）
ssh-keygen -t rsa -b 4096

# 公開鍵を監視対象サーバーにコピー
ssh-copy-id monitor@192.168.1.10
```

#### パスワード認証

`hosts.json`に`ssh_password`を設定するだけで使用できます。ただし、パスワードが平文で保存されるため、セキュリティリスクがあります。

### 5. Discordボットの作成

1. [Discord Developer Portal](https://discord.com/developers/applications)でアプリケーションを作成
2. Botを追加してTokenを取得
3. Bot Permissionsで以下を有効化:
   - Send Messages
   - Embed Links
   - Read Message History
4. OAuth2 URL Generatorでボットをサーバーに招待

## 実行

```bash
python bot.py
```

## コマンド

ボット起動後、Discordで以下のコマンドが使用可能:

- `!status` - 全サーバーのステータスを表示
- `!status <hostname>` - 特定サーバーのステータスを表示
- `!uptime <hostname>` - 特定サーバーのアップタイム履歴を表示

## ファイル構成

```
dcmt/
├── bot.py              # メインのボットロジック
├── monitor.py          # システム情報取得（SSH経由）
├── ssh_client.py       # SSH接続管理
├── uptime_tracker.py   # アップタイム履歴管理
├── config.py           # 設定管理
├── hosts.json          # 監視対象ホストの設定
├── uptime_history.db   # アップタイム履歴データベース（自動生成）
├── .env               # 環境変数（要作成）
├── .env.example       # 環境変数テンプレート
├── .gitignore         # Git除外設定
├── requirements.txt   # 依存パッケージ
└── README.md          # このファイル
```

## トラブルシューティング

### SSH接続エラー

- SSH鍵のパスが正しいか確認
- 監視対象サーバーでSSHサービスが起動しているか確認
- ファイアウォールでSSHポート（デフォルト22）が開放されているか確認

### Discordボットが起動しない

- `.env`ファイルの`DISCORD_TOKEN`が正しいか確認
- `CHANNEL_ID`が正しいか確認（開発者モードで取得可能）

### データが表示されない

- `hosts.json`の設定が正しいか確認
- 監視対象サーバーで必要なコマンド（`top`, `free`, `df`等）が利用可能か確認

## ライセンス

MIT License