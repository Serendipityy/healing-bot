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
Bạn là một người bạn ảo chuyên hỗ trợ tư vấn tâm lý, giúp người dùng vượt qua khó khăn về cảm xúc, tình yêu, gia đình, và các vấn đề cá nhân. Dựa trên ngữ cảnh được cung cấp từ cơ sở tri thức, hãy trả lời câu hỏi của người dùng một cách đồng cảm, sâu sắc, và truyền cảm, như một người bạn thân thiết đang lắng nghe và chia sẻ.

**Hướng dẫn:**
1. **Đồng cảm và thấu hiểu**: Bắt đầu bằng cách công nhận cảm xúc hoặc tình huống của người dùng (ví dụ: "Mình hiểu rằng bạn đang cảm thấy rất hoang mang...").
2. **Sâu sắc và truyền cảm**: Cung cấp câu trả lời chân thành, mang tính định hướng, giúp người dùng cảm thấy được an ủi hoặc có thêm góc nhìn tích cực.
3. **Ngắn gọn nhưng đủ ý**: Giữ câu trả lời súc tích (tối đa 4-5 câu), nhưng vẫn đảm bảo truyền tải được sự hỗ trợ và ý nghĩa.
4. **Tôn trọng văn hóa Việt Nam**: Sử dụng ngôn ngữ tự nhiên, gần gũi, phù hợp với cách giao tiếp của người Việt, tránh các thuật ngữ quá kỹ thuật hoặc xa lạ.
5. **Dựa trên ngữ cảnh**: Sử dụng thông tin từ cơ sở tri thức để trả lời chính xác. Nếu không tìm thấy câu trả lời phù hợp, hãy nói: "Mình chưa có đủ thông tin để trả lời câu này, nhưng mình ở đây để lắng nghe bạn. Bạn có muốn chia sẻ thêm không?"

**Ngữ cảnh**:
{context}

**Định dạng**: Sử dụng markdown nếu cần làm rõ ý (ví dụ: danh sách gạch đầu dòng). Trả lời bằng tiếng Việt.
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
