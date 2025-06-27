import re
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
   - Có thể dùng emoji (🥹, 🫶, 😤, 🐸, ✨…) nếu phù hợp với ngữ cảnh.
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
Bạn là một chuyên gia trong lĩnh vực tư vấn tâm lý và chăm sóc sức khỏe tinh thần.

Hãy phân loại câu hỏi (chỉ dựa theo phần "Câu hỏi", không dựa vào phần "Câu trả lời tham khảo") dưới đây dựa trên mức độ thông tin mà người hỏi cần:
- Trả lời **"summary"** nếu câu hỏi quá ngắn gọn hoặc yêu cầu đơn giản, một cái nhìn tổng quan, định hướng, hoặc lời khuyên chung.
- Trả lời **"full"** nếu câu hỏi yêu cầu phân tích sâu, thông tin chi tiết, hoặc phản hồi mang tính cá nhân hóa cao.

Chỉ trả lời một từ duy nhất: "summary" hoặc "full".

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
    # Step 1: LLM router chain
    routing_chain = ROUTING_PROMPT | llm | RunnableLambda(lambda output: output.content.strip().lower())

    # Step 2: dynamic retriever routing
    def get_retriever(routing_output: str) -> VectorStoreRetriever:
        return retriever_summary if routing_output == "summary" else retriever_full

    def retrieve_context(inputs: dict) -> List[Document]:
        question = inputs["question"]
        routing_output = routing_chain.invoke({"question": question})
        print(f"🧭 Type: {routing_output}")
        retriever = get_retriever(routing_output)
        retriever_config = retriever.with_config({"run_name": f"context_retriever_{routing_output}"})
        return retriever_config.invoke(question)

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
            # 🔍 DEBUG: Print retrieved documents
            documents = event["data"]["output"]
            print(f"\n{'='*80}")
            print(f"📚 RETRIEVED DOCUMENTS DEBUG")
            print(f"{'='*80}")
            print(f"🔍 Question: {question[:100]}{'...' if len(question) > 100 else ''}")
            print(f"📊 Number of documents retrieved: {len(documents) if documents else 0}")
            
            if documents:
                for i, doc in enumerate(documents[:3], 1):  # Show first 3 docs
                    print(f"\n📄 Document {i}:")
                    print(f"   Content: {doc.page_content[:200]}{'...' if len(doc.page_content) > 200 else ''}")
                    if hasattr(doc, 'metadata') and doc.metadata:
                        print(f"   Metadata: {doc.metadata}")
                        
                if len(documents) > 3:
                    print(f"\n... and {len(documents) - 3} more documents")
            else:
                print("❌ No documents retrieved!")
            print(f"{'='*80}\n")
            
            yield documents
        if event_type == "on_chain_stream":
            yield event["data"]["chunk"].content
