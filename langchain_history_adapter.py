from langchain_core.chat_history import BaseChatMessageHistory

from langchain_memory import append_messages, clear_history, get_history_messages


class SQLiteChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id: str):
        self.session_id = str(session_id or "").strip() or "anonymous"

    @property
    def messages(self):
        return get_history_messages(self.session_id)

    def add_messages(self, messages):
        append_messages(self.session_id, *messages)

    def clear(self):
        clear_history(self.session_id)


def get_session_history(session_id: str):
    return SQLiteChatMessageHistory(session_id=session_id)
