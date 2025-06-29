# ベースイメージ
FROM python:3.10-slim

# コンテナのタイムゾーンをアジア/東京に設定
ENV TZ=Asia/Tokyo

# cronとタイムゾーンデータをインストール
RUN apt-get update && apt-get install -y --no-install-recommends cron tzdata && \
    rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ
WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# デフォルトコマンド
CMD ["python", "main.py"]