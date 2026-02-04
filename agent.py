"""
Agent module for the Nova Educational Bot.
Uses the new google-genai SDK for latest API compatibility.
Includes retry logic for rate limit handling.
"""

from google import genai
from google.genai import types
from typing import Optional, Tuple
import re
import time

from config import GOOGLE_API_KEY, TEMPERATURE, BOT_NAME
from tools import (
    search_wikipedia, search_web, search_youtube_videos,
    calculate, SUBJECT_AREAS
)
from memory import ConversationMemory

# Create the client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY = 5  # seconds


class SimpleKnowledgeBot:
    """
    Educational Knowledge Bot using the new google-genai SDK.
    Features memory, multiple knowledge tools, subject modes, and ELI5.
    """
    
    def __init__(self, session_id: str, subject: str = "general", eli5_mode: bool = False):
        self.session_id = session_id
        self.subject = subject
        self.eli5_mode = eli5_mode
        self.memory = ConversationMemory(session_id)
        self.model_name = "models/gemini-2.5-flash"
    
    def set_subject(self, subject: str):
        """Change the subject focus."""
        if subject in SUBJECT_AREAS:
            self.subject = subject
    
    def set_eli5_mode(self, enabled: bool):
        """Toggle ELI5 mode."""
        self.eli5_mode = enabled
    
    def _get_subject_context(self) -> str:
        """Get subject-specific context."""
        subject_info = SUBJECT_AREAS.get(self.subject, SUBJECT_AREAS["general"])
        return f"Subject focus: {subject_info['name']} {subject_info['icon']}"
    
    def _is_quiz_request(self, text: str) -> bool:
        """Check if user is asking for a quiz."""
        quiz_keywords = ['quiz', 'test me', 'practice questions', 'questions about', 'test my knowledge']
        return any(kw in text.lower() for kw in quiz_keywords)
    
    def _is_flashcard_request(self, text: str) -> bool:
        """Check if user is asking for flashcards."""
        flashcard_keywords = ['flashcard', 'flash card', 'study cards', 'vocabulary cards', 'create cards']
        return any(kw in text.lower() for kw in flashcard_keywords)
    
    def _is_video_request(self, text: str) -> bool:
        """Check if user is asking for videos."""
        video_keywords = ['video', 'youtube', 'watch', 'tutorial video', 'show me a video']
        return any(kw in text.lower() for kw in video_keywords)
    
    def _is_calculation_request(self, text: str) -> bool:
        """Check if user is asking for a calculation."""
        calc_keywords = ['calculate', 'compute', 'what is', 'solve', 'equals']
        has_numbers = bool(re.search(r'\d+\s*[\+\-\*\/\^]\s*\d+', text))
        return has_numbers or any(kw in text.lower() for kw in calc_keywords)
    
    def chat(self, user_input: str) -> Tuple[str, bool, Optional[str]]:
        """Process user input with enhanced educational features."""
        try:
            tool_results = ""
            used_tools = False
            
            # Handle different types of requests
            if self._is_calculation_request(user_input):
                match = re.search(r'[\d\.\+\-\*\/\^\(\)\s]+', user_input)
                if match:
                    calc_result = calculate(match.group().strip())
                    if "Error" not in calc_result:
                        tool_results = f"\n\n{calc_result}"
                        used_tools = True
            
            if self._is_video_request(user_input):
                video_result = search_youtube_videos(user_input)
                if "Error" not in video_result and "No educational videos" not in video_result:
                    tool_results += f"\n\n{video_result}"
                    used_tools = True
            
            # Check if we need to search for info
            search_keywords = ['who is', 'what is', 'where is', 'when did', 'how did', 'tell me about', 'explain']
            needs_search = any(kw in user_input.lower() for kw in search_keywords)
            
            if needs_search and not self._is_quiz_request(user_input) and not self._is_flashcard_request(user_input):
                wiki_result = search_wikipedia(user_input)
                if "No Wikipedia articles found" not in wiki_result and "Error" not in wiki_result:
                    tool_results += f"\n\nRelevant information:\n{wiki_result}"
                    used_tools = True
                else:
                    web_result = search_web(user_input)
                    if "No web results found" not in web_result and "Error" not in web_result:
                        tool_results += f"\n\nRelevant information:\n{web_result}"
                        used_tools = True
            
            # Get conversation context
            history = self.memory.get_messages()
            context = "\n".join([f"{'Human' if m['role']=='user' else 'Assistant'}: {m['content']}" 
                                for m in history[-6:]])
            
            # Build the prompt
            subject_info = SUBJECT_AREAS.get(self.subject, SUBJECT_AREAS["general"])
            subject_context = f"Subject focus: {subject_info['name']} {subject_info['icon']}"
            
            eli5_instruction = ""
            if self.eli5_mode:
                eli5_instruction = """
🧒 ELI5 MODE ACTIVE: Explain EVERYTHING as if talking to a 5-year-old child.
- Use only simple, everyday words
- Use fun comparisons like "it's like when you..."
- Keep sentences very short
- Use lots of friendly emojis
- Make it fun and exciting!
"""
            
            # Special handling for quiz requests
            if self._is_quiz_request(user_input):
                prompt = f"""You are Nova, an educational AI. Create an engaging quiz!
{subject_context}
{eli5_instruction}

Previous conversation:
{context if context else 'This is the start of our conversation.'}

User request: {user_input}

Create a fun quiz with 3-5 multiple choice questions. Format each question like this:

🎯 **Quiz Time!**

**Question 1:** [Question]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

(Continue with more questions)

---
📝 **Answers:**
1. [Correct answer with brief explanation]
2. [Correct answer with brief explanation]
..."""
            
            elif self._is_flashcard_request(user_input):
                prompt = f"""You are Nova, an educational AI. Create helpful study flashcards!
{subject_context}
{eli5_instruction}

Previous conversation:
{context if context else 'This is the start of our conversation.'}

User request: {user_input}

Create 5 flashcards for studying. Format like this:

📚 **Study Flashcards**

---
**Card 1**
📝 **Front:** [Question or term]
💡 **Back:** [Answer or definition]

---
**Card 2**
📝 **Front:** [Question or term]
💡 **Back:** [Answer or definition]

(Continue with more cards)

💪 **Study tip:** [A helpful tip for remembering this topic]"""
            
            else:
                prompt = f"""You are Nova, a friendly and knowledgeable educational AI assistant.
{subject_context}
{eli5_instruction}

Previous conversation:
{context if context else 'This is the start of our conversation.'}

{tool_results}

User: {user_input}

Respond helpfully and naturally. Be warm and use emojis appropriately.
If there's relevant information provided above, use it to give an accurate answer.
If the user asks a follow-up question, refer to the person or topic from the previous conversation."""

            # Generate response using the new SDK with retry logic
            response_text = None
            last_error = None
            
            for attempt in range(MAX_RETRIES):
                try:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=TEMPERATURE,
                        )
                    )
                    response_text = response.text
                    break  # Success, exit retry loop
                except Exception as api_error:
                    last_error = api_error
                    error_str = str(api_error).lower()
                    if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                            continue
                    else:
                        raise api_error
            
            if response_text is None:
                return f"⏳ Rate limit reached. Please wait {RETRY_DELAY} seconds and try again.", False, None
            
            # Save to memory
            self.memory.add_interaction(user_input, response_text)
            
            return response_text, used_tools, None
            
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}", False, None
    
    def get_conversation_history(self) -> list:
        return self.memory.get_messages()
    
    def clear_memory(self):
        self.memory.clear()


# Alias for compatibility
KnowledgeBot = SimpleKnowledgeBot


def create_simple_bot(session_id: str, subject: str = "general", eli5_mode: bool = False) -> SimpleKnowledgeBot:
    """Create a bot instance."""
    return SimpleKnowledgeBot(session_id, subject, eli5_mode)
