import logging
import os
import time
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from ragbase.config import Config

load_dotenv()

list_keys = [
    "AIzaSyBhSDC69kLBqw21VdsYvBs74q98w4dHa7E",
    # "AIzaSyDaVCYIC-j6BoBe4VEWPRMWnR7hTu9puZo",
    # "AIzaSyBfmOEpr9mdfyEimLW1wQh9Ik4drMAdyF8",
    # "AIzaSyCZ6lZNrFesfPtSkixvmaH7b8TX-UMUVBg",
    # "AIzaSyDVjszXsue2Qs7rQf4-VNHhUt-1KZtQdx4",
    # "AIzaSyDQMVfzyVcytu_4I32Hh6_xwVQA2G2nr30",
    # "AIzaSyAtDL5ryd6oIUAKjp4cFnTgW21xPynp6YY",
    # "AIzaSyDha2zavpRp2fkrpVz6Xopv6HppcyubX2Y",
    # "AIzaSyBSLdACUAR5srrD_yoolWKtIZlIk5JtMSo",
    # "AIzaSyB17vRD3BlCe0gzOCbvbrgwwC7zVTXlbZo",
    # "AIzaSyCVA6ctW4cXNUzwUqYkR6pWbBSdh19zwvA",
    # "AIzaSyCNLh5HhlIUovo8_de1RWg1jAx2Iq4Yo8g",
    # "AIzaSyD_d2NNsNxVhWLK_d2yjnEQuyTNUECi1Ns",
    # "AIzaSyCw371rlLG4FqlRan4C0rD280sqVga-zE4",
    # "AIzaSyBctBtlbRv4aJ5cvJRZNK_sfPiBY8-6KoY",
    # "AIzaSyAMKQvJs5hAup1JUNl3G29dt24m5mRLgiE",
]

class QueryTransformationHyDE:
    def __init__(self):
        self.keys = list_keys
        self.model = None
        self.current_key_index = 0
        self._configure_model(self.keys[self.current_key_index])

    def _configure_model(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        # logging.info(f"✅ Using API key index {self.current_key_index}")

    def _retry_with_next_key(self) -> bool:
        self.current_key_index += 1
        if self.current_key_index < len(self.keys):
            self._configure_model(self.keys[self.current_key_index])
            return True
        return False

    def transform_query(self, query: str) -> str:
        prompt = f"""
        Bạn là một người bạn tâm giao, luôn lắng nghe và chia sẻ những kinh nghiệm sống chân thành.

        Hãy viết một đoạn văn ngắn gọn (2-3 câu) phản ánh về câu hỏi sau, như thể bạn đang chia sẻ kinh nghiệm hoặc suy nghĩ cá nhân:

        🔎 Câu hỏi: "{query}"

        Yêu cầu:
        - Viết như lời tâm sự, không phải lời khuyên chuyên môn
        - Ngắn gọn, súc tích, bám sát chủ đề
        - Thể hiện sự đồng cảm và hiểu biết thực tế
        - Tránh dùng từ ngữ chuyên môn tâm lý
        **Trả lời bằng tiếng Việt**.
        """

        retry_attempts = 0
        max_attempts = len(self.keys)

        while retry_attempts < max_attempts:
            try:
                response = self.model.generate_content(prompt)
                generated_response = response.text.strip()
                return f"Câu hỏi: {query}\nCâu trả lời tham khảo: {generated_response}"
            except Exception as e:
                error_message = str(e)
                logging.warning(f"❌ Attempt {retry_attempts + 1} failed: {error_message}")
                if "429" in error_message or "Rate limit" in error_message:
                    time.sleep(2)  # Delay to avoid hammering
                    if not self._retry_with_next_key():
                        logging.error("🚫 All API keys exhausted.")
                        raise RuntimeError("⚠️ All Gemini API keys failed due to rate limiting.")
                    retry_attempts += 1
                else:
                    raise RuntimeError(f"⚠️ Gemini failed: {e}")

