import sqlite3
import logging
from config import DB_FILE, CONTRIBUTION_WEIGHTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """データベース接続を取得する"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベーステーブルを初期化（作成）する"""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts_analysis (
                    post_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    posted_at TIMESTAMP NOT NULL,
                    reaction_count INTEGER DEFAULT 0,
                    is_violation BOOLEAN NOT NULL,
                    violation_reason TEXT,
                    is_positive BOOLEAN NOT NULL,
                    is_helpful_answer BOOLEAN NOT NULL, 
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                );
            """)
        logging.info("データベースの初期化が完了しました。")
    except sqlite3.Error as e:
        logging.error(f"データベース初期化エラー: {e}")
    finally:
        conn.close()

def save_analysis_result(post_data):
    """投稿の分析結果を保存する"""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO posts_analysis 
                (post_id, user_id, channel_id, posted_at, reaction_count, is_violation, violation_reason, is_positive, is_helpful_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data['post_id'],
                post_data['user_id'],
                post_data['channel_id'],
                post_data['posted_at'],
                post_data['reaction_count'],
                post_data['is_violation'],
                post_data['violation_reason'],
                post_data['is_positive'],
                post_data['is_helpful_answer']
            ))
    except sqlite3.Error as e:
        logging.error(f"分析結果の保存に失敗しました (post_id: {post_data.get('post_id')}): {e}")
    finally:
        conn.close()

def upsert_user(user_id, user_name):
    """ユーザー情報を保存または更新する"""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO users (user_id, user_name) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET user_name = excluded.user_name;
            """, (user_id, user_name))
    except sqlite3.Error as e:
        logging.error(f"ユーザー情報の保存に失敗しました (user_id: {user_id}): {e}")
    finally:
        conn.close()

def update_user_score(user_id, user_name, score):
    """ユーザーのスコアと名前を更新または新規作成する"""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO users (user_id, user_name, contribution_score, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                user_name = excluded.user_name,
                contribution_score = contribution_score + ?,
                updated_at = CURRENT_TIMESTAMP;
            """, (user_id, user_name, score, score))
    except sqlite3.Error as e:
        logging.error(f"ユーザースコアの更新に失敗しました (user_id: {user_id}): {e}")
    finally:
        conn.close()

def get_user_stats(start_time, end_time):
    """指定期間内のユーザーアクティビティを集計する"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                user_id,
                COUNT(post_id) as post_count,
                SUM(reaction_count) as total_reactions,
                SUM(CASE WHEN is_positive = 1 THEN 1 ELSE 0 END) as positive_post_count
            FROM posts_analysis
            WHERE posted_at BETWEEN ? AND ?
            GROUP BY user_id
        """, (start_time, end_time))
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"ユーザー統計の取得に失敗しました: {e}")
        return []
    finally:
        conn.close()
        
def get_violation_posts(start_time, end_time):
    """指定期間内の違反投稿を取得する"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT post_id, user_id, channel_id, violation_reason
            FROM posts_analysis
            WHERE is_violation = 1 AND posted_at BETWEEN ? AND ?
        """, (start_time, end_time))
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"違反投稿の取得に失敗しました: {e}")
        return []
    finally:
        conn.close()

def get_ranking(start_time, end_time, limit=20):
    """指定期間の活動を集計し、貢献度ランキングを生成する"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # posts_analysisから期間内の活動を集計し、usersテーブルと結合してランキングを生成
        query = f"""
            SELECT
                u.user_name,
                (
                    COUNT(p.post_id) * {CONTRIBUTION_WEIGHTS['post_count']} +
                    SUM(p.reaction_count) * {CONTRIBUTION_WEIGHTS['reaction_count']} +
                    SUM(CASE WHEN p.is_positive = 1 THEN 1 ELSE 0 END) * {CONTRIBUTION_WEIGHTS['positive_post_count']} +
                    SUM(CASE WHEN p.is_helpful_answer = 1 THEN 1 ELSE 0 END) * {CONTRIBUTION_WEIGHTS['answer_contribution']}
                ) as total_score
            FROM posts_analysis p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.posted_at BETWEEN ? AND ?
            GROUP BY p.user_id
            ORDER BY total_score DESC
            LIMIT ?
        """
        cursor.execute(query, (start_time, end_time, limit))
        return cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"ランキングの取得に失敗しました: {e}")
        return []
    finally:
        conn.close()