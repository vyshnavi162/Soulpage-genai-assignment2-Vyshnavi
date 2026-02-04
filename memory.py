"""
Memory module for the Conversational Knowledge Bot.
Handles conversation memory and persistent storage.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from config import CHAT_HISTORY_DIR, MAX_HISTORY_LENGTH


# Simple message class for fallback
class SimpleMessage:
    def __init__(self, content: str, msg_type: str):
        self.content = content
        self.type = msg_type


# Simple chat memory for fallback
class SimpleChatMemory:
    def __init__(self):
        self.messages = []
    
    def add_user_message(self, content: str):
        self.messages.append(SimpleMessage(content, "human"))
    
    def add_ai_message(self, content: str):
        self.messages.append(SimpleMessage(content, "ai"))


# Try different import paths for different LangChain versions
ConversationBufferMemory = None
try:
    from langchain.memory import ConversationBufferMemory
except ImportError:
    try:
        from langchain_community.memory import ConversationBufferMemory
    except ImportError:
        pass  # Will use fallback


class ChatHistoryManager:
    """Manages persistent chat history storage."""
    
    def __init__(self):
        self.history_dir = CHAT_HISTORY_DIR
        os.makedirs(self.history_dir, exist_ok=True)
    
    def _get_filepath(self, session_id: str) -> str:
        """Get the file path for a session's history."""
        return os.path.join(self.history_dir, f"{session_id}.json")
    
    def save_conversation(self, session_id: str, messages: List[Dict], title: str = None):
        """Save conversation to disk."""
        filepath = self._get_filepath(session_id)
        
        # Generate title from first message if not provided
        if not title and messages:
            first_user_msg = next((m for m in messages if m.get("role") == "user"), None)
            if first_user_msg:
                title = first_user_msg.get("content", "")[:50] + "..."
        
        data = {
            "session_id": session_id,
            "title": title or "New Conversation",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": messages[-MAX_HISTORY_LENGTH:]  # Keep only recent messages
        }
        
        # Preserve original created_at if file exists
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    data["created_at"] = existing.get("created_at", data["created_at"])
            except:
                pass
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_conversation(self, session_id: str) -> Optional[Dict]:
        """Load conversation from disk."""
        filepath = self._get_filepath(session_id)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None
    
    def get_all_conversations(self) -> List[Dict]:
        """Get all saved conversations, sorted by most recent."""
        conversations = []
        
        for filename in os.listdir(self.history_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.history_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        conversations.append({
                            "session_id": data.get("session_id"),
                            "title": data.get("title", "Untitled"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "message_count": len(data.get("messages", []))
                        })
                except:
                    continue
        
        # Sort by updated_at, most recent first
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations
    
    def delete_conversation(self, session_id: str) -> bool:
        """Delete a conversation."""
        filepath = self._get_filepath(session_id)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False


class ConversationMemory:
    """Wrapper around LangChain's ConversationBufferMemory with persistence."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history_manager = ChatHistoryManager()
        self._use_langchain = ConversationBufferMemory is not None
        
        if self._use_langchain:
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                input_key="input",
                output_key="output"
            )
            self.chat_memory = self.memory.chat_memory
        else:
            # Fallback to simple memory
            self.chat_memory = SimpleChatMemory()
        
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Load conversation history from disk into memory."""
        saved = self.history_manager.load_conversation(self.session_id)
        
        if saved and saved.get("messages"):
            for msg in saved["messages"]:
                if msg.get("role") == "user":
                    self.chat_memory.add_user_message(msg.get("content", ""))
                elif msg.get("role") == "assistant":
                    self.chat_memory.add_ai_message(msg.get("content", ""))
    
    def add_interaction(self, user_input: str, bot_response: str):
        """Add a new interaction to memory and save to disk."""
        self.chat_memory.add_user_message(user_input)
        self.chat_memory.add_ai_message(bot_response)
        self._save_to_disk()
    
    def _save_to_disk(self):
        """Save current memory state to disk."""
        messages = []
        for msg in self.chat_memory.messages:
            role = "user" if msg.type == "human" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content
            })
        
        self.history_manager.save_conversation(self.session_id, messages)
    
    def get_messages(self) -> List[Dict]:
        """Get all messages in current memory."""
        messages = []
        for msg in self.chat_memory.messages:
            role = "user" if msg.type == "human" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content
            })
        return messages
    
    def clear(self):
        """Clear memory."""
        if self._use_langchain:
            self.memory.clear()
        else:
            self.chat_memory.messages = []
    
    def get_langchain_memory(self) -> ConversationBufferMemory:
        """Get the underlying LangChain memory object."""
        return self.memory
