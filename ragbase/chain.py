import re
import time
from operator import itemgetter
from typing import List

from langchain.schema.runnable import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import (ChatPromptTemplate, MessagesPlaceholder,
                                    PromptTemplate)
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tracers.stdout import ConsoleCallbackHandler
from langchain_core.vectorstores import VectorStoreRetriever

from ragbase.config import Config
from ragbase.session_history import get_session_history

SYSTEM_PROMPT = """
Bạn là một người bạn thân ảo – như tri kỷ online – luôn đồng hành cùng người dùng qua những tâm sự cảm xúc (buồn, vui, stress, thất tình, gia đình, tình bạn), những câu hỏi triết lý sâu sắc, hoặc chỉ đơn giản là một lời khuyên ngắn gọn. Mục tiêu là tạo cảm giác như đang trò chuyện với một người thật – có thể đùa giỡn, thủ thỉ, cà khịa nhẹ nhàng, hoặc vỗ về yêu thương – chứ không phải nói chuyện với máy.

⚠️ **Nguyên tắc quan trọng**:
1. Luôn bám sát ngữ cảnh được cung cấp, không tự ý thêm thông tin không có trong context
2. Điều chỉnh giọng điệu phù hợp với từng loại câu hỏi/tâm trạng người dùng
3. Tránh lặp lại các cụm từ mở đầu quá công thức

---

**Hướng dẫn trả lời chi tiết:**

1. **Phân loại và phản hồi phù hợp**:
   - Với tâm sự buồn/cảm xúc: "Tớ hiểu cảm giác này...", "Nghe cậu chia sẻ mà..."
   - Với câu hỏi triết lý: "Đây là một câu hỏi thú vị...", "Theo góc nhìn của tớ..."
   - Với thắc mắc thông thường: Đi thẳng vào vấn đề, trả lời rõ ràng
   - Khi không rõ context: "Cậu có thể kể thêm cho tớ nghe được không?"

2. **Xử lý ngữ cảnh**:
   - Nếu context có sẵn câu trả lời: Diễn đạt lại tự nhiên hơn nhưng giữ nguyên ý nghĩa và văn phong gốc
   - Nếu context không đủ: Thẳng thắn thừa nhận và gợi mở câu chuyện
   - Tuyệt đối không bịa thông tin ngoài context

3. **Văn phong tự nhiên**:
   - Tránh bullet point, viết thành đoạn văn mạch lạc
   - Hạn chế dùng ngoặc kép trích dẫn, thay bằng cách diễn đạt gián tiếp
   - Có thể dùng emoji (😤, 🐸, ✨…) nếu phù hợp với ngữ cảnh.
   - Câu văn có nhịp điệu, tránh đều đều

4. **Xưng hô linh hoạt**:
   - Mặc định: "cậu - tớ" nếu người dùng chưa xác định
   - Bắt chước cách xưng hô của người dùng nếu họ chủ động
   - Không thay đổi cách xưng hô giữa chừng

---

**Ngữ cảnh đã truy xuất:**  
{context}

**Yêu cầu đầu ra:**
- Tiếng Việt tự nhiên, gần gũi
- Giọng điệu phù hợp với từng tình huống
- Bám sát context nhưng diễn đạt mềm mại
- Tránh công thức, linh hoạt trong cách mở đầu
"""



# Prompt dùng để phân loại câu hỏi
ROUTING_PROMPT = PromptTemplate.from_template("""
Bạn là một chuyên gia phân loại câu hỏi tâm lý và chăm sóc sức khỏe tinh thần.

Phân loại câu hỏi dưới đây (chỉ dựa theo "Câu hỏi", bỏ qua "Câu trả lời tham khảo"):

**Trả lời "full" nếu:**
- Câu hỏi về triết lý nhân sinh, ý nghĩa cuộc sống (VD: "tuổi nào thì được phép chênh vênh", "nếu cả đời không rực rỡ thì sao")
- Yêu cầu phân tích tâm lý sâu sắc hoặc lời khuyên chi tiết
- Câu hỏi phức tạp về mối quan hệ, tình cảm
- Chia sẻ câu chuyện dài cần tư vấn cụ thể

**Trả lời "summary" nếu:**
- Câu hỏi đơn giản về định nghĩa, khái niệm cơ bản
- Yêu cầu thông tin tổng quan, hướng dẫn chung
- Câu hỏi ngắn gọn không cần phân tích sâu

Chỉ trả lời một từ: "summary" hoặc "full".

Câu hỏi: {question}
""")

def remove_links(text: str) -> str:
    url_pattern = r"https?://\S+|www\.\S+"
    return re.sub(url_pattern, "", text)


def format_documents(documents: List[Document]) -> str:
    texts = []
    for doc in documents:
        texts.append(doc.page_content)
        texts.append("---")

    return remove_links("\n".join(texts))


def create_chain(llm: BaseLanguageModel, retriever_full: VectorStoreRetriever, retriever_summary: VectorStoreRetriever) -> Runnable:
    # Step 1: Optimized routing - use simple heuristics for common cases
    def smart_route(question: str) -> str:
        question_lower = question.lower()
        
        # Simple heuristics to avoid LLM call for routing
        simple_keywords = ['là gì', 'nghĩa là gì', 'định nghĩa', 'khái niệm', 'ý nghĩa của']
        complex_keywords = ['tại sao', 'làm thế nào', 'phải làm gì', 'cách nào', 'giải quyết']
        
        # Quick routing based on keywords
        for keyword in simple_keywords:
            if keyword in question_lower:
                print(f"🚀 Quick route: summary (keyword: {keyword})")
                return "summary"
                
        for keyword in complex_keywords:
            if keyword in question_lower:
                print(f"🚀 Quick route: full (keyword: {keyword})")
                return "full"
        
        # Fallback to LLM routing for unclear cases
        routing_chain = ROUTING_PROMPT | llm | RunnableLambda(lambda output: output.content.strip().lower())
        result = routing_chain.invoke({"question": question})
        print(f"🧭 LLM Route: {result}")
        return result

    # Step 2: dynamic retriever routing with timing
    def get_retriever(routing_output: str) -> VectorStoreRetriever:
        return retriever_summary if routing_output == "summary" else retriever_full

    def retrieve_context(inputs: dict) -> List[Document]:
        question = inputs["question"]
        
        routing_start = time.time()
        routing_output = smart_route(question)
        routing_end = time.time()
        print(f"⚡ Routing took: {routing_end - routing_start:.2f}s")
        
        retriever = get_retriever(routing_output)
        retriever_config = retriever.with_config({"run_name": f"context_retriever_{routing_output}"})
        
        # Retrieval with timing
        retrieval_start = time.time()
        docs = retriever_config.invoke(question)
        retrieval_end = time.time()
        print(f"⚡ Retrieval took: {retrieval_end - retrieval_start:.2f}s")
        
        print(f"📄 Retrieved {len(docs)} documents from {routing_output}")
        
        return docs

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{question}"),
        ]
    )

    chain = (
        RunnablePassthrough.assign(
            context=RunnableLambda(retrieve_context) | format_documents
        )
        | prompt
        | llm
    )

    return RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    ).with_config({"run_name": "chain_answer"})

async def ask_question(chain: Runnable, question: str, session_id: str):
    async for event in chain.astream_events(
        {"question": question},
        config={
            "callbacks": [ConsoleCallbackHandler()] if Config.DEBUG else [],
            "configurable": {"session_id": session_id},
        },
        version="v2",
        include_names=[
            "context_retriever_full",
            "context_retriever_summary",
            "chain_answer",
        ],
    ):
        event_type = event["event"]
        if event_type == "on_retriever_end":
            yield event["data"]["output"]
        if event_type == "on_chain_stream":
            yield event["data"]["chunk"].content
