from typing import List, Dict
from collections import defaultdict
from config import MAX_CONVERSATION_TURNS

class ConversationMemory:
    def __init__(self):
        # Init histories registry
        self._histories: Dict[str, List[Dict]] = defaultdict(list)

    def add_turn(self, session_id: str, role: str, content: str):
        # Log turn details
        self._histories[session_id].append({"role": role, "content": content})
        limit = MAX_CONVERSATION_TURNS * 2
        if len(self._histories[session_id]) > limit:
            self._histories[session_id] = self._histories[session_id][-limit:]

    def get_history(self, session_id: str) -> List[Dict]:
        # Fetch session list
        return self._histories.get(session_id, [])

    def get_context_string(self, session_id: str) -> str:
        # Build prompt string
        history = self.get_history(session_id)
        if not history:
            return ""
        lines = []
        for turn in history[-MAX_CONVERSATION_TURNS * 2:]:
            role = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{role}: {turn['content']}")
        return "\n".join(lines)

    def clear_session(self, session_id: str):
        # Delete session history
        if session_id in self._histories:
            del self._histories[session_id]

    def clear_all(self):
        # Reset entire memory
        self._histories.clear()
