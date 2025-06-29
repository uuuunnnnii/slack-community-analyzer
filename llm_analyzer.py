import google.generativeai as genai
import logging
import json
from config import GEMINI_API_KEY, LLM_PROMPT

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def analyze_post(post_text: str = False) -> dict:
    """投稿テキストをLLMで分析し、結果を辞書で返す。返信かどうかでプロンプトを切り替える。"""
    
    prompt = LLM_PROMPT.format(post_text=post_text)
    default_response = {
        "is_violation": False,
        "violation_reason": "",
        "is_positive": False,
        "is_helpful_answer": False
    }
    expected_keys = {
        "is_violation": bool, 
        "violation_reason": (str, type(None)), 
        "is_positive": bool,
        "is_helpful_answer": bool
    }

    try:
        response = model.generate_content(prompt)
        json_text = response.text.strip().lstrip("```json").rstrip("```")
        analysis = json.loads(json_text)

        # デフォルトレスポンスに分析結果をマージ（不足キーを補う）
        analysis = default_response | analysis

        # 想定したキーと型が含まれているかチェック
        for key, value_type in expected_keys.items():
            if not isinstance(analysis[key], value_type):
                logging.warning(f"LLMからのレスポンス形式が不正です (key: {key}): {analysis}")
                return default_response
        
        return analysis

    except Exception as e:
        logging.error(f"LLMによる投稿分析に失敗しました: {e}")
        return default_response