import logging
import datetime
from zoneinfo import ZoneInfo
from time import sleep
import config
import database
import slack_client
import llm_analyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_daily_batch():
    """1日1回のバッチ処理を実行する"""
    logging.info("--- バッチ処理を開始します ---")

    # 1. 処理対象期間を設定 (前日3:00 〜 当日2:59)
    JST = ZoneInfo("Asia/Tokyo")
    now = datetime.datetime.now(JST)
    # now = datetime.datetime(2025, 6, 30, 3, 0, 0, tzinfo=JST) # デバッグ用に固定日時を設定
    end_time = now.replace(hour=3, minute=0, second=0, microsecond=0)
    start_time = end_time - datetime.timedelta(days=1)
    
    start_time_ts = str(start_time.timestamp())
    end_time_ts = str(end_time.timestamp())
    
    logging.info(f"処理対象期間: {start_time} ~ {end_time}")

    # 2. データ取得と分析
    channels_to_process = []
    if config.TARGET_CHANNELS:
        channels_to_process = config.TARGET_CHANNELS
        logging.info(f"config.pyで指定されたチャンネルのみを処理します: {channels_to_process}")
    # 値がなければ、全ての公開チャンネルを対象とする（除外リストはslack_client側で処理）
    else:
        channels_to_process = slack_client.get_all_public_channels()
        logging.info("全ての公開チャンネルを処理対象とします。")
    
    total_posts_processed = 0
    user_names_cache = {}  # ユーザー名キャッシュ

    for channel_id in channels_to_process:
        messages = slack_client.get_messages_from_channel(channel_id, start_time_ts, end_time_ts)
        sleep(3) # APIレートリミット対策 (Slack)

        for msg in messages:
            # Bot、除外ユーザー、チャンネル参加メッセージはスキップ
            # if ("user" not in msg or
            #         msg.get("user") in config.EXCLUDED_USER_IDS or
            #         msg.get("bot_id") or
            #         msg.get("subtype") == "channel_join"):
            #     logging.info(f"スキップ: ユーザーID {msg.get('user')}、subtype {msg.get('subtype')} の投稿は除外対象です。")
            #     continue

            # ユーザー情報をDBに保存/更新 (名前が変わる可能性があるため)
            if msg["user"] not in user_names_cache:
                user_name = slack_client.get_user_name(msg["user"])
                user_names_cache[msg["user"]] = user_name
                database.upsert_user(msg["user"], user_name)
                sleep(0.5)

            # 3. 投稿分析
            # スレッドへの返信かどうかを判定
            analysis_result = llm_analyzer.analyze_post(msg["text"])

            # 4. 結果の保存
            post_data = {
                "post_id": msg["ts"],
                "user_id": msg["user"],
                "channel_id": channel_id,
                "posted_at": datetime.datetime.fromtimestamp(float(msg["ts"])),
                "reaction_count": len(msg.get("reactions", [])),
                "is_violation": analysis_result["is_violation"],
                "violation_reason": analysis_result["violation_reason"],
                "is_positive": analysis_result["is_positive"],
                "is_helpful_answer": analysis_result["is_helpful_answer"]
            }
            database.save_analysis_result(post_data)
            total_posts_processed += 1
            logging.info(f'"{msg["text"]}","{analysis_result["is_helpful_answer"]}","{analysis_result["is_positive"]}","{analysis_result["is_violation"]}","{analysis_result["violation_reason"]}"')
            sleep(10) # APIレートリミット対策（Gemini）

    logging.info(f"合計{total_posts_processed}件の投稿を分析・保存しました。")

    # 5. 違反投稿の通知
    logging.info("違反の可能性がある投稿を通知します。")
    violation_posts = database.get_violation_posts(start_time, end_time)
    for post in violation_posts:
        # キャッシュされたユーザー名を利用
        user_name = user_names_cache.get(post["user_id"], "不明なユーザー")
        permalink = slack_client.get_permalink(post["channel_id"], post["post_id"])
        
        notification_text = (
            f"ガイドライン違反の可能性がある投稿が検出されました。\n"
            f"投稿者: {user_name}\n"
            f"判定理由: {post['violation_reason']}\n"
            f"リンク: {permalink}"
        )
        slack_client.post_message(config.ADMIN_CHANNEL_ID, notification_text)
        sleep(1)

    # 6. ランキング投稿
    logging.info("貢献度ランキングを投稿します。")
    # 期間を指定してランキングを生成（今回は日次バッチなので前日分を集計）
    ranking = database.get_ranking(start_time, end_time, limit=20) 
    
    ranking_text = f"{start_time.strftime('%Y/%m/%d')}の貢献度ランキングTOP20 :tada:\n"
    if not ranking:
        ranking_text += "昨日の活動はありませんでした。"
    else:
        for i, user in enumerate(ranking):
            # user['total_score'] は float の可能性があるため整数に丸める
            ranking_text += f"{i+1}. {user['user_name']}: {round(user['total_score'])}点\n"
    
    # 通知したいチャンネルIDを指定
    slack_client.post_message(config.RANKING_CHANNEL_ID, ranking_text)

    logging.info("--- バッチ処理が正常に終了しました ---")

if __name__ == "__main__":
    # 初回実行時にデータベースを初期化
    database.init_db()
    # バッチ処理を実行
    run_daily_batch()