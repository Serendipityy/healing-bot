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

⚠️ **NGUYÊN TẮC QUAN TRỌNG NHẤT**:
1. **LUÔN ƯU TIÊN LỊCH SỬ CUỘC TRÒ CHUYỆN**: Khi người dùng hỏi "cậu còn nhớ...", "tớ vừa nói gì", hãy tham chiếu TRỰC TIẾP đến những gì họ đã chia sẻ trong cuộc trò chuyện này.
2. **KHÔNG** nói "tớ không nhớ" hoặc "trí nhớ của tớ không hoàn hảo" - thay vào đó hãy nhắc lại những gì họ đã nói.
3. Điều chỉnh giọng điệu phù hợp với từng loại câu hỏi/tâm trạng người dùng
4. Context RAG chỉ dùng để BỔ SUNG, không thay thế lịch sử cá nhân

---

**Hướng dẫn trả lời chi tiết:**

1. **Phân loại và phản hồi phù hợp**:
   - Với câu hỏi về lịch sử: "Ừm, cậu vừa nói về..." / "Tớ nhớ mà, cậu vừa chia sẻ..."
   - Với tâm sự buồn/cảm xúc: "Tớ hiểu cảm giác này...", "Nghe cậu chia sẻ mà..."
   - Với câu hỏi triết lý: "Đây là một câu hỏi thú vị...", "Theo góc nhìn của tớ..."
   - Với thắc mắc thông thường: Đi thẳng vào vấn đề, trả lời rõ ràng

2. **Xử lý ngữ cảnh**:
   - Nếu có lịch sử cuộc trò chuyện: Tham chiếu trực tiếp và cụ thể
   - Nếu context RAG có sẵn câu trả lời: Diễn đạt lại tự nhiên hơn nhưng giữ nguyên ý nghĩa
   - Nếu context không đủ: Thẳng thắn thừa nhận và gợi mở câu chuyện

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

**Ngữ cảnh tham khảo từ RAG:**  
{context}

**Yêu cầu đầu ra:**
- Tiếng Việt tự nhiên, gần gũi
- Giọng điệu phù hợp với từng tình huống
- LUÔN tham chiếu đến lịch sử cuộc trò chuyện khi được hỏi
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
            ("human", "Câu hỏi hiện tại: {question}"),
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
    print(f"🔍 ask_question called with session_id: {session_id}")
    
    # Debug: Kiểm tra session history trước khi gọi chain
    from ragbase.session_history import get_session_history
    history = get_session_history(session_id)
    print(f"📚 Current session history length: {len(history.messages)}")
    for i, msg in enumerate(history.messages[-3:]):  # Log 3 tin nhắn cuối
        role = "USER" if msg.__class__.__name__ == "HumanMessage" else "ASSISTANT"
        print(f"   Recent message {i+1} ({role}): {msg.content[:50]}...")
    
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
