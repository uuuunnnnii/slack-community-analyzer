import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# --- Slack API設定 ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID") # 違反通知用のチャンネル
RANKING_CHANNEL_ID = os.getenv("RANKING_CHANNEL_ID") # ランキング投稿用のチャンネル

# --- 分析対象外ユーザー ---
# BotのIDなどを設定
EXCLUDED_USER_IDS = {""}

# --- 分析対象チャンネル (特定のチャンネルのみを対象としたい場合に設定) ---
# この設定が空の場合、全てのパブリックチャンネルが対象になります（SKIPPED_CHANNELSを除く）。
TARGET_CHANNELS = {"XXXXX"}

# --- 分析対象外チャンネル ---
# チャンネルIDのリスト
SKIPPED_CHANNELS = {""}


# --- Gemini API設定 ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- データベース設定 ---
DB_FILE = "slack_bot.db"

# --- スコアリング設定 ---
# Score = (投稿数 * w1) + (獲得リアクション総数 * w2) + (ポジティブ投稿数 * w3) + (回答貢献度 * w4)
CONTRIBUTION_WEIGHTS = {
    "post_count": 1,        # w1
    "reaction_count": 2,    # w2
    "positive_post_count": 3, # w3
    "answer_contribution": 5, # w4
}

# --- LLMへのプロンプト設定 ---
LLM_PROMPT = """
あなたはSlackコミュニティのモデレーターです。
以下の投稿が、私たちのコミュニティガイドラインに違反している可能性、および他者への感謝や称賛といったポジティブな内容であるかを分析してください。

# コミュニティガイドライン
- 他者への敬意を忘れないこと。誹謗中傷、嫌がらせ、差別的な発言は禁止です。
- 個人情報（氏名、所属、住所、電話番号、メールアドレスなど）の投稿は禁止です。
- 営業、宣伝、勧誘を目的とした投稿は禁止です。

# 投稿テキスト
\"\"\"
{post_text}
\"\"\"

# 出力形式
以下のJSON形式のみで、他のテキストは含めずに回答してください。
- is_violation: ガイドライン違反の可能性が高い場合は true, そうでなければ false。
- violation_reason: is_violationがtrueの場合、その理由を簡潔に記述。
- is_positive: 投稿が他者への感謝、称賛、励ましなどポジティブな内容を含む場合は true, そうでなければ false。
- is_helpful_answer: 投稿が質問に対する有益な回答である場合は true, そうでなければ false。

{{
  "is_violation": boolean,
  "violation_reason": "具体的な違反理由",
  "is_positive": boolean,
  "is_helpful_answer": boolean
}}
"""