# Slack Community Analyzer

Slackコミュニティの健全化と活性化を目的とした、AIによる日次投稿分析バッチシステムです。

## 概要

このシステムは、Slackの公開チャンネルの投稿を毎日自動で収集し、Google Gemini APIを利用して内容を分析します。
分析結果に基づき、不適切な投稿の管理者への通知や、コミュニティ貢献度の高いユーザーのランキング発表を自動で行います。

**採択プロジェクト:** [PJT-09: Slackの発言を監視するBot]

## 機能一覧

- **ガイドライン違反検知**: 個人情報や誹謗中傷など、不適切な投稿をAIが検知し、管理者へ通知します。
- **ポジティブ投稿分析**: 他者への感謝や称賛といった、コミュニティの雰囲気を良くする投稿を判定します。
- **貢献度スコアリング**: 投稿数、獲得リアクション数、投稿内容のポジティブさなどを基に、独自のロジックでユーザーの貢献度を算出します。
- **日次ランキング通知**: 算出した貢献度スコアを基に、毎日のランキングを生成し、指定チャンネルへ投稿します。
- **柔軟な設定**: 分析対象外のユーザーやチャンネルを`config.py`で簡単に設定できます。

## 使用技術

- **言語**: Python 3.10
- **主要ライブラリ**:
  - `slack_sdk`: Slack APIとの連携
  - `google-generativeai`: Google Gemini APIとの連携
  - `python-dotenv`: 環境変数の管理
- **AIモデル**: Gemini 2.0 Flash
- **データベース**: SQLite3

## 構成 (Architecture)
```
┌───────────────────────────────────────────────┐
│  Slack Workspace         管理者ch / ランキングch │
└──────────┬───────────────────────┬────────────┘
           │                       ▲
    ① メッセージ取得             ⑤ 通知・投稿
           │                       │
           v                       │
    ┌─────────────────────────────────────────┐
    │             メインプログラム               │
    │       夜間3時バッチ・前日3時〜1日分集計      │
    └───────┬──────────────────────┬──────────┘
            │                      │
       ② 分析依頼            ④ DB操作（保存・取得）
            v                      v
   ┌─────────────────┐      ┌─────────────────┐
   │    Gemini API   │      │      SQLite     │
   └─────────────────┘      └─────────────────┘
```

## 環境構築（事前準備）

### Slackアプリの作成とBot Tokenの取得
1. Slackアプリの作成
- [Slack API](https://api.slack.com/apps)サイトにアクセスし、「Create New App」をクリックします。
- 「From scratch」を選択し、アプリ名（例: monitoring-bot）と、インストール先のワークスペースを指定して「Create App」をクリックします。

2. Botスコープの設定
- 左側のメニューから「OAuth & Permissions」を選択します。
- 「Scopes」セクションまでスクロールし、「Bot Token Scopes」にある「Add an OAuth Scope」をクリックします。
- ボットに必要な権限を付与します。最低限、以下の4つを追加してください。
  - channels:read ワークスペース内の公開チャンネルの一覧を取得するために必要
  - channels:history  公開チャンネルのメッセージ履歴を読み取るために必要
  - users:read    投稿者のユーザー情報を取得するために必要
  - chat:write    チャンネルにメッセージを投稿するために必要

3. アプリのインストールとトークンの取得
- ページ上部の「OAuth Tokens」セクションへスクロールし、「Install to ワークスペース名」をクリックし、表示される手順に従ってアプリをワークスペースにインストールします。
- インストールが完了すると、「OAuth & Permissions」ページに「Bot User OAuth Token」が表示されます。このトークン（xoxb-で始まる文字列）をコピーしておきます。これが環境変数 SLACK_BOT_TOKEN の値になります。

### Google AI (Gemini) APIキーの取得
1. [Google AI Studio](https://aistudio.google.com/)にアクセスします。
2. 「Get API key」をクリックし、新しいAPIキーを作成してコピーします。

## 環境構築（実行方法）

1.  **リポジトリをクローン**

    ```bash
    git clone [https://github.com/](https://github.com/)uuuunnnnii/slack-monitoring-bot.git
    cd slack-community-analyzer
    ```

2.  **環境変数を設定**

    `.env.example` を参考に `.env` ファイルを作成し、必要なAPIキー等を設定してください。
    ```bash
    cp .env.example .env
    # .env ファイルを編集
    ```

3.  **データベースファイルの作成**

    ホスト側に空のデータベースファイルを作成します。
    ```bash
    touch slack_bot.db
    ```

4.  **Dockerイメージをビルド**

    `docker-compose.yml` の設定に基づいて、アプリケーションの実行環境となるDockerイメージを作成します。
    ```bash
    docker-compose build
    ```

5.  **定期実行の設定**

    夜間3時にコンテナを起動し、`main.py` を実行します。`--rm` オプションにより、実行後はコンテナが自動で削除されます。
    ```crontab
    # macOSの場合の例
    0 3 * * * /bin/bash -c 'cd /Users/your_username/my-slack-bot-project && /usr/local/bin/docker-compose run --rm slack-bot python main.py >> /Users/your_username/my-slack-bot-project/cron.log 2>&1'
    #
    # Linuxの場合の例
    # 0 3 * * * /bin/bash -c 'cd /home/your_username/my-slack-bot-project && /usr/local/bin/docker-compose run --rm slack-bot python main.py >> /home/your_username/my-slack-bot-project/cron.log 2>&1'
    ```

    一発ターミナルから実行する場合
    ```bash
    docker-compose run --rm slack-bot python main.py
    ```

## ディレクトリ構成
```
.
├── Dockerfile              # Dockerイメージの設計図
├── docker-compose.yml      # Dockerコンテナの構成管理ファイル
├── main.py                 # メイン実行スクリプト
├── slack_client.py         # Slack API連携モジュール
├── llm_analyzer.py         # Gemini API分析モジュール
├── database.py             # DB操作モジュール
├── config.py               # 設定ファイル
├── requirements.txt        # 依存ライブラリ
└── README.md               # このファイル
```
