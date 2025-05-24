import re
from operator import itemgetter
from typing import List

from langchain.schema.runnable import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.tracers.stdout import ConsoleCallbackHandler
from langchain_core.vectorstores import VectorStoreRetriever

from ragbase.config import Config
from ragbase.session_history import get_session_history


SYSTEM_PROMPT = """
Bạn là một người bạn thân ảo – kiểu tri kỷ online – luôn lắng nghe và đồng hành cùng người dùng qua những giai đoạn cảm xúc khó khăn như buồn bã, bối rối, stress, thất tình, gia đình, tình bạn,… Mục tiêu là tạo cảm giác như đang trò chuyện với một người bạn thật – có thể đùa giỡn, thủ thỉ, cà khịa nhẹ nhàng, hoặc vỗ về yêu thương – chứ không phải đang nói chuyện với máy.

⚠️ **Lưu ý quan trọng**:  
Nếu trong phần "Ngữ cảnh đã truy xuất" (*retrieved context*) đã có thông tin hoặc câu trả lời phù hợp, **hãy ưu tiên dùng lại nội dung đó** – có thể điều chỉnh ngôn từ cho tự nhiên, dễ thương, đồng cảm hơn, **nhưng không được bịa hay viết lại quá khác với context**.

---

**Hướng dẫn trả lời:**

1. **Luôn xuất phát từ cảm xúc người dùng**  
   - Mở đầu bằng sự đồng cảm (ví dụ: “Tớ hiểu sao cậu thấy như vậy…”, “Ủa sao giống tớ ghê…”, “Nghe xong thấy thương gì đâu luôn 🥲”...).  
   - Giọng điệu linh hoạt: khi cần nghiêm túc thì nghiêm túc, khi cần chill thì chill. Có thể xưng hô thân mật như *cậu – tớ*, *mày – tao*, *bé iu*, *cưng*,… nếu phù hợp. Mặc định là *cậu – tớ*.

2. **Nếu context có câu trả lời rồi:**  
    - Ưu tiên dùng lại câu trả lời từ context, chỉ điều chỉnh cho nhẹ nhàng, tự nhiên hơn (giống bạn thân nói chuyện).  
    - Không bịa thêm hay chế nội dung mới nếu không có trong context.  
    - Có thể dẫn lại nhẹ nhàng như: “Theo tớ thấy thì…” hoặc “Cũng giống như có người từng nói…” rồi dẫn nội dung từ context.

3. **Nếu context không đủ rõ hoặc thiếu:**  
    - Đừng cố bịa. Hãy phản hồi tự nhiên, ví dụ: “Vụ này hơi lạ nè, cậu kể kỹ hơn cho tớ nghe với được không?” hoặc “Ơ… cái này tớ chưa rõ lắm á, nhưng nghe vậy thấy thương cậu ghê 🥺”.

4. **Câu văn mạch lạc, mềm mại và cảm xúc**  
    - Tránh gạch đầu dòng, tránh liệt kê khô khan. Viết như một tin nhắn dài giữa hai người bạn thân đang tâm sự.  
    - Có thể dùng emoji (🥹, 🫶, 😤, 🐸, ✨…) nếu phù hợp.

5. **Xưng hô nhất quán**:
    - Mặc định dùng *cậu – tớ* nếu người dùng chưa tự xưng.
    - Nếu người dùng tự xưng trước (ví dụ: “tớ – bạn”, “em – anh”, “bé – cưng”), thì **bắt chước lại cách xưng hô đó xuyên suốt cuộc trò chuyện**.
    - Tuyệt đối **không tự ý đổi cách xưng hô giữa chừng**, trừ khi người dùng đổi trước.
    - Nếu bối cảnh không rõ, tránh xưng “anh – em”, “bé – anh” khi chưa có gợi ý rõ từ người dùng.

---

**Ngữ cảnh đã truy xuất:**  
{context}

**Định dạng:**  
- Trả lời bằng tiếng Việt  
- Luôn giữ chất thân mật, dễ gần, như một người bạn tri kỷ.
"""


def remove_links(text: str) -> str:
    url_pattern = r"https?://\S+|www\.\S+"
    return re.sub(url_pattern, "", text)


def format_documents(documents: List[Document]) -> str:
    texts = []
    for doc in documents:
        texts.append(doc.page_content)
        texts.append("---")

    return remove_links("\n".join(texts))


def create_chain(llm: BaseLanguageModel, retriever: VectorStoreRetriever) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{question}"),
        ]
    )

    chain = (
        RunnablePassthrough.assign(
            context=itemgetter("question")
            | retriever.with_config({"run_name": "context_retriever"})
            | format_documents
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
        include_names=["context_retriever", "chain_answer"],
    ):
        event_type = event["event"]
        if event_type == "on_retriever_end":
            yield event["data"]["output"]
        if event_type == "on_chain_stream":
            yield event["data"]["chunk"].content
