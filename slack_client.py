from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from slack_sdk.http_retry import all_builtin_retry_handlers
from config import SLACK_BOT_TOKEN, SKIPPED_CHANNELS

# リトライハンドラを初期化
retry_handlers = all_builtin_retry_handlers()

client = WebClient(
    token=SLACK_BOT_TOKEN,
    retry_handlers=retry_handlers
)

def get_all_public_channels():
    """全ての公開チャンネルIDを取得する"""
    try:
        result = client.conversations_list(types="public_channel")
        return [c["id"] for c in result["channels"]]
    except SlackApiError as e:
        logging.error(f"チャンネルリストの取得に失敗しました: {e}")
        return []

def join_channel_if_not_member(channel_id):
    """ボットがチャンネルのメンバーでない場合、参加する"""
    try:
        # チャンネル情報を取得して、ボットが既にメンバーか確認する
        # is_memberはボットが参加している場合のみtrueを返す
        info = client.conversations_info(channel=channel_id)
        if info["channel"].get("is_member"):
            # logging.info(f"既に参加済みです (Channel: {channel_id})")
            return True

        # メンバーでない場合は参加する
        logging.info(f"チャンネルに参加します (Channel: {channel_id})")
        client.conversations_join(channel=channel_id)
        return True
    except SlackApiError as e:
        # プライベートチャンネルやアーカイブ済みチャンネルなどで失敗することがある
        if e.response["error"] == "method_not_supported_for_channel_type":
             logging.warning(f"このチャンネルタイプには参加できません (Channel: {channel_id})")
        elif e.response["error"] == "not_in_channel":
             # conversations.infoがnot_in_channelを返すのは正常。この後joinする。
             try:
                 logging.info(f"チャンネルに参加します (Channel: {channel_id})")
                 client.conversations_join(channel=channel_id)
                 return True
             except SlackApiError as join_e:
                 logging.error(f"チャンネルへの参加に失敗しました (Channel: {channel_id}): {join_e}")
                 return False
        else:
            logging.error(f"チャンネル情報の取得または参加に失敗しました (Channel: {channel_id}): {e}")
        return False

def get_messages_from_channel(channel_id, start_time_ts, end_time_ts):
    """指定チャンネルから指定期間のメッセージを取得する"""
    # チャンネルIDが除外リストに含まれている場合はスキップ
    if channel_id in SKIPPED_CHANNELS:
        logging.info(f"設定によりメッセージ履歴の取得をスキップします (Channel: {channel_id})")
        return []

    messages = []
    # メッセージ取得の前に、チャンネルに参加する処理を呼び出す
    if not join_channel_if_not_member(channel_id):
        logging.warning(f"チャンネルに参加できなかったため、メッセージ取得をスキップします (Channel: {channel_id})")
        return [] # 参加に失敗したら空のリストを返す
    try:
        for page in client.conversations_history(
            channel=channel_id,
            latest=end_time_ts,
            oldest=start_time_ts,
            limit=200 # 1回のリクエストで取得する最大件数
        ):
            messages.extend(page["messages"])
    except SlackApiError as e:
        logging.error(f"メッセージの取得に失敗しました (Channel: {channel_id}): {e}")
        
    logging.info(f"チャンネル({channel_id})から{len(messages)}件のメッセージを取得しました。")
    return messages
    
def get_user_name(user_id):
    """ユーザーIDからユーザー名を取得する"""
    try:
        result = client.users_info(user=user_id)
        return result["user"]["real_name"] or result["user"]["name"]
    except SlackApiError as e:
        logging.error(f"ユーザー情報の取得に失敗しました (User: {user_id}): {e}")
        return "不明なユーザー"

def get_permalink(channel_id, message_ts):
    """メッセージのパーマリンクを取得する"""
    try:
        result = client.chat_getPermalink(channel=channel_id, message_ts=message_ts)
        return result["permalink"]
    except SlackApiError as e:
        logging.error(f"パーマリンクの取得に失敗しました (Channel: {channel_id}, TS: {message_ts}): {e}")
        return ""

def post_message(channel_id, text, blocks=None):
    """指定チャンネルにメッセージを投稿する"""
    try:
        client.chat_postMessage(channel=channel_id, text=text, blocks=blocks)
        logging.info(f"メッセージを投稿しました (Channel: {channel_id})")
    except SlackApiError as e:
        logging.error(f"メッセージの投稿に失敗しました (Channel: {channel_id}): {e}")