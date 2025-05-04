# from langchain_community.chat_message_histories import ChatMessageHistory

# store = {}


# def get_session_history(session_id: str) -> ChatMessageHistory:
#     if session_id not in store:
#         store[session_id] = ChatMessageHistory()
#     return store[session_id]


from langchain_community.chat_message_histories import ChatMessageHistory

store = {}


def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def save_chat_history(session_id: str, history_data: dict):
    """
    Lưu lịch sử chat vào bộ nhớ hoặc cơ sở dữ liệu
    """

    if "chat_histories" not in store:
        store["chat_histories"] = {}
    
    store["chat_histories"][session_id] = history_data


def get_all_chat_histories():
    """
    Lấy tất cả lịch sử chat đã lưu
    """
    if "chat_histories" not in store:
        return []
    
    return list(store["chat_histories"].values())