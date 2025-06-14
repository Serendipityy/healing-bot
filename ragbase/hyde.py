import logging
import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from ragbase.config import Config

load_dotenv()

class QueryTransformationHyDE:
    def __init__(self):
        """
        Initialize the QueryTransformation class with Gemini model.

        :param api_key: Your Gemini API key.
        """
        api_key =  os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("⚠️ Gemini API key is missing. Please set GEMINI_API_KEY in your .env file.")

        genai.configure(api_key=api_key)
        self.model = model = genai.GenerativeModel("gemini-2.0-flash")

    def transform_query(self, query: str) -> str:
        """
        Generates a hypothetical document from the user's query using Gemini.
        This output is used for embedding or retrieval tasks.

        :param query: User's input question or query.
        :return: Hypothetical document string.
        """
        prompt = f"""
        Bạn là một chuyên gia tư vấn tâm lý và sức khỏe tinh thần.

        Hãy trả lời câu truy vấn sau một cách tự nhiên, chân thành, sâu sắc và đầy cảm thông:

        🔎 Truy vấn từ người dùng:
        "{query}"

        Đoạn văn nên thể hiện sự thấu hiểu cảm xúc, gợi mở hướng nhìn tích cực, và mang lại cảm giác được lắng nghe và chữa lành. 
        **Trả lời bằng bằng tiếng Việt**.
        """

        try:
            response = self.model.generate_content(prompt)
            generated_response = response.text.strip()
            return f"Câu hỏi: {query}\nCâu trả lời tham khảo: {generated_response}"
            return response.text.strip()
        except Exception as e:
            logging.error(f"❌ Failed to generate hypothetical document: {e}")
            raise RuntimeError("⚠️ Gemini failed to generate hypothetical document.")