"""
Nova - Educational Knowledge Bot
A premium ChatGPT/Gemini-style chat interface with memory, educational tools,
subject modes, and ELI5 (Explain Like I'm 5) mode.
"""

import streamlit as st
import uuid
import time
from datetime import datetime
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Nova - Educational Bot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_file = Path(__file__).parent / "styles.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Import after config to avoid issues
from config import GOOGLE_API_KEY, BOT_NAME, BOT_AVATAR, USER_AVATAR
from memory import ChatHistoryManager
from agent import SimpleKnowledgeBot, KnowledgeBot
from tools import SUBJECT_AREAS

# Initialize session state
def init_session_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "bot" not in st.session_state:
        st.session_state.bot = None
    if "is_typing" not in st.session_state:
        st.session_state.is_typing = False
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
    if "subject" not in st.session_state:
        st.session_state.subject = "general"
    if "eli5_mode" not in st.session_state:
        st.session_state.eli5_mode = False

init_session_state()

# History manager
history_manager = ChatHistoryManager()

# Sidebar
def render_sidebar():
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎓</div>
            <h1 style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-size: 1.75rem;
                margin: 0;
            ">Nova</h1>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin-top: 0.25rem;">
                Your Educational Companion
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Subject Mode Selector
        st.markdown("""
        <div class="sidebar-title">📚 Subject Mode</div>
        """, unsafe_allow_html=True)
        
        subject_options = {key: f"{val['icon']} {val['name']}" for key, val in SUBJECT_AREAS.items()}
        selected_subject = st.selectbox(
            "Choose subject focus",
            options=list(subject_options.keys()),
            format_func=lambda x: subject_options[x],
            index=list(subject_options.keys()).index(st.session_state.subject),
            key="subject_selector",
            label_visibility="collapsed"
        )
        
        if selected_subject != st.session_state.subject:
            st.session_state.subject = selected_subject
            if st.session_state.bot:
                st.session_state.bot.set_subject(selected_subject)
            st.rerun()
        
        # ELI5 Mode Toggle
        st.markdown("<br>", unsafe_allow_html=True)
        eli5_col1, eli5_col2 = st.columns([3, 1])
        with eli5_col1:
            st.markdown("""
            <div style="color: #a0a0b0; font-size: 0.9rem;">
                🧒 <strong>ELI5 Mode</strong><br>
                <span style="font-size: 0.75rem;">Simplified explanations</span>
            </div>
            """, unsafe_allow_html=True)
        with eli5_col2:
            eli5_toggle = st.toggle("", value=st.session_state.eli5_mode, key="eli5_toggle", label_visibility="collapsed")
            if eli5_toggle != st.session_state.eli5_mode:
                st.session_state.eli5_mode = eli5_toggle
                if st.session_state.bot:
                    st.session_state.bot.set_eli5_mode(eli5_toggle)
                st.rerun()
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("""
        <div class="sidebar-title">⚡ Quick Actions</div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎯 Quiz", use_container_width=True, key="quick_quiz"):
                return "generate_quiz"
            if st.button("🧮 Math", use_container_width=True, key="quick_math"):
                return "calculate"
        with col2:
            if st.button("📝 Cards", use_container_width=True, key="quick_cards"):
                return "generate_flashcards"
            if st.button("🎬 Videos", use_container_width=True, key="quick_videos"):
                return "find_videos"
        
        st.markdown("---")
        
        # New chat button
        if st.button("✨ New Chat", use_container_width=True, key="new_chat"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.bot = None
            st.session_state.show_welcome = True
            st.rerun()
        
        st.markdown("---")
        
        # Chat history
        st.markdown("""
        <div class="sidebar-title">
            📜 Chat History
        </div>
        """, unsafe_allow_html=True)
        
        conversations = history_manager.get_all_conversations()
        
        if conversations:
            for conv in conversations[:10]:  # Show last 10 conversations
                is_active = conv["session_id"] == st.session_state.session_id
                
                # Format date
                try:
                    updated = datetime.fromisoformat(conv["updated_at"])
                    date_str = updated.strftime("%b %d, %I:%M %p")
                except:
                    date_str = "Unknown"
                
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    if st.button(
                        f"{'🔵 ' if is_active else '💬 '}{conv['title'][:30]}...",
                        key=f"hist_{conv['session_id']}",
                        use_container_width=True
                    ):
                        # Load this conversation
                        st.session_state.session_id = conv["session_id"]
                        loaded = history_manager.load_conversation(conv["session_id"])
                        if loaded:
                            st.session_state.messages = loaded.get("messages", [])
                            st.session_state.bot = None
                            st.session_state.show_welcome = False
                        st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{conv['session_id']}", help="Delete"):
                        history_manager.delete_conversation(conv["session_id"])
                        if conv["session_id"] == st.session_state.session_id:
                            st.session_state.session_id = str(uuid.uuid4())
                            st.session_state.messages = []
                            st.session_state.bot = None
                        st.rerun()
        else:
            st.markdown("""
            <p style="color: #6b6b7b; text-align: center; padding: 1rem;">
                No conversations yet.<br>Start chatting! 💬
            </p>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Bot status
        api_status = "🟢 Connected" if GOOGLE_API_KEY else "🔴 No API Key"
        subject_info = SUBJECT_AREAS.get(st.session_state.subject, SUBJECT_AREAS["general"])
        eli5_status = "🧒 ELI5 On" if st.session_state.eli5_mode else ""
        
        st.markdown(f"""
        <div style="padding: 1rem; background: #252538; border-radius: 0.75rem; margin-top: 1rem;">
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">
                <strong>Status:</strong> {api_status}
            </p>
            <p style="color: #6b6b7b; font-size: 0.75rem; margin: 0.5rem 0 0 0;">
                {subject_info['icon']} {subject_info['name']} {eli5_status}
            </p>
            <p style="color: #6b6b7b; font-size: 0.75rem; margin: 0.5rem 0 0 0;">
                Powered by Google Gemini
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    return None


def render_welcome():
    """Render the welcome screen using native Streamlit components."""
    subject_info = SUBJECT_AREAS.get(st.session_state.subject, SUBJECT_AREAS["general"])
    
    # Welcome header
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <div style="font-size: 5rem; margin-bottom: 1rem;">🎓</div>
            <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                font-size: 2.5rem; margin: 0;">Hello! I'm Nova</h1>
            <p style="color: #a0a0b0; font-size: 1.1rem; margin-top: 0.5rem;">
                Your intelligent educational companion
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Feature cards using Streamlit columns
    st.markdown("### ✨ What I Can Do For You")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">🎯</div>
            <h4 style="color: white; margin: 0.5rem 0;">Quizzes</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Test your knowledge with interactive quizzes</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">🧮</div>
            <h4 style="color: white; margin: 0.5rem 0;">Calculator</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Solve math problems instantly</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">📝</div>
            <h4 style="color: white; margin: 0.5rem 0;">Flashcards</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Create study cards for any topic</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">🧒</div>
            <h4 style="color: white; margin: 0.5rem 0;">ELI5 Mode</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Simple explanations for beginners</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">🎬</div>
            <h4 style="color: white; margin: 0.5rem 0;">Videos</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Find educational videos on YouTube</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #252538; border-radius: 1rem; padding: 1.5rem; text-align: center; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.1);">
            <div style="font-size: 2.5rem;">📚</div>
            <h4 style="color: white; margin: 0.5rem 0;">Subject Focus</h4>
            <p style="color: #a0a0b0; font-size: 0.85rem; margin: 0;">Specialized learning by subject</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Suggestion chips based on subject
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Try asking me:**")
    
    subject_suggestions = {
        "general": [
            "Quiz me on world capitals",
            "Explain quantum physics",
            "Create flashcards for photosynthesis",
            "Find videos about black holes"
        ],
        "math": [
            "Calculate 456 * 789",
            "Explain the Pythagorean theorem",
            "Quiz me on fractions",
            "Create flashcards for algebra"
        ],
        "science": [
            "Explain how DNA works",
            "Quiz me on the periodic table",
            "Create flashcards for chemistry",
            "Find videos about evolution"
        ],
        "history": [
            "Tell me about World War 2",
            "Quiz me on ancient Rome",
            "Create flashcards for US presidents",
            "Find videos about the Renaissance"
        ],
        "literature": [
            "Explain Shakespeare's themes",
            "Quiz me on literary devices",
            "Create flashcards for poetry terms",
            "Who wrote To Kill a Mockingbird?"
        ],
        "programming": [
            "Explain what is an API",
            "Quiz me on Python basics",
            "Create flashcards for data structures",
            "Find videos about machine learning"
        ],
        "geography": [
            "Name the longest river",
            "Quiz me on countries",
            "Create flashcards for continents",
            "Find videos about climate zones"
        ],
        "art": [
            "Who painted the Mona Lisa?",
            "Quiz me on art movements",
            "Create flashcards for music theory",
            "Find videos about impressionism"
        ]
    }
    
    suggestions = subject_suggestions.get(st.session_state.subject, subject_suggestions["general"])
    
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                return suggestion
    
    return None


def render_message(role: str, content: str, show_animation: bool = False):
    """Render a single message bubble."""
    if role == "user":
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
            <div class="message-bubble user-message" {'style="animation: slideIn 0.3s ease-out;"' if show_animation else ''}>
                {content}
            </div>
            <div class="avatar user-avatar" style="margin-left: 0.75rem;">
                {USER_AVATAR}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Process markdown for bot messages
        st.markdown(f"""
        <div style="display: flex; margin-bottom: 1rem;">
            <div class="avatar bot-avatar" style="margin-right: 0.75rem;">
                {BOT_AVATAR}
            </div>
            <div class="message-bubble bot-message" {'style="animation: slideIn 0.3s ease-out;"' if show_animation else ''}>
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_typing_indicator():
    """Render the typing animation."""
    st.markdown("""
    <div style="display: flex; margin-bottom: 1rem;">
        <div class="avatar bot-avatar" style="margin-right: 0.75rem;">
            🎓
        </div>
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def get_or_create_bot():
    """Get or create the bot instance."""
    if st.session_state.bot is None:
        try:
            # Try the full agent first
            st.session_state.bot = KnowledgeBot(
                st.session_state.session_id,
                subject=st.session_state.subject,
                eli5_mode=st.session_state.eli5_mode
            )
        except Exception:
            # Fall back to simple bot
            st.session_state.bot = SimpleKnowledgeBot(
                st.session_state.session_id,
                subject=st.session_state.subject,
                eli5_mode=st.session_state.eli5_mode
            )
    return st.session_state.bot


def process_message(user_input: str):
    """Process user input and get bot response."""
    if not GOOGLE_API_KEY:
        return "⚠️ Please set your GOOGLE_API_KEY in the .env file to use Nova.", False
    
    bot = get_or_create_bot()
    
    try:
        response, used_tools, diagram = bot.chat(user_input)
        
        # Add tool indicator if tools were used
        if used_tools:
            response += "\n\n<span class='tool-indicator'>🔍 Searched for information</span>"
        
        return response, True
    except Exception as e:
        return f"I'm sorry, I encountered an error: {str(e)}", False


def main():
    # Render sidebar and get any quick action
    quick_action = render_sidebar()
    
    # Main content area
    subject_info = SUBJECT_AREAS.get(st.session_state.subject, SUBJECT_AREAS["general"])
    eli5_badge = "🧒 ELI5" if st.session_state.eli5_mode else ""
    
    st.markdown(f"""
    <div style="text-align: center; padding: 0.5rem 0;">
        <span style="color: #a0a0b0; font-size: 0.85rem;">
            <span class="status-dot"></span>Nova is ready to help • {subject_info['icon']} {subject_info['name']} {eli5_badge}
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for API key
    if not GOOGLE_API_KEY:
        st.warning("""
        ⚠️ **API Key Required**  
        Please create a `.env` file with your Google Gemini API key:  
        ```
        GOOGLE_API_KEY=your_key_here
        ```
        Get your free API key from [Google AI Studio](https://aistudio.google.com/)
        """)
    
    # Handle quick actions
    quick_action_prompts = {
        "generate_quiz": f"Generate a quiz about {subject_info['name']}",
        "generate_flashcards": f"Create flashcards for {subject_info['name']}",
        "find_videos": f"Find educational videos about {subject_info['name']}",
        "calculate": "Help me with a math calculation"
    }
    
    if quick_action and quick_action in quick_action_prompts:
        st.session_state.show_welcome = False
        quick_input = quick_action_prompts[quick_action]
        
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": quick_input
        })
        
        # Get response
        response, success = process_message(quick_input)
        
        # Add bot response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        
        # Save to history
        history_manager.save_conversation(
            st.session_state.session_id,
            st.session_state.messages
        )
        
        st.rerun()
    
    # Welcome screen or chat
    suggestion_clicked = None
    if st.session_state.show_welcome and not st.session_state.messages:
        suggestion_clicked = render_welcome()
    
    # Display chat messages
    if st.session_state.messages:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for i, msg in enumerate(st.session_state.messages):
            show_animation = (i >= len(st.session_state.messages) - 2)
            render_message(msg["role"], msg["content"], show_animation)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Use a form for better UX
    with st.form(key="chat_form", clear_on_submit=True):
        cols = st.columns([6, 1])
        with cols[0]:
            user_input = st.text_input(
                "Message",
                placeholder=f"Ask {BOT_NAME} anything...",
                label_visibility="collapsed",
                key="user_input"
            )
        with cols[1]:
            submit = st.form_submit_button("Send ➤", use_container_width=True)
    
    # Handle suggestion click
    if suggestion_clicked:
        user_input = suggestion_clicked
        submit = True
    
    # Process input
    if submit and user_input:
        st.session_state.show_welcome = False
        
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Show typing indicator (will be replaced on rerun)
        with st.spinner(""):
            response, success = process_message(user_input)
        
        # Add bot response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        
        # Save to history
        history_manager.save_conversation(
            st.session_state.session_id,
            st.session_state.messages
        )
        
        st.rerun()
    
    # Footer
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1rem 0; color: #6b6b7b; font-size: 0.8rem;">
        Nova 🎓 • Powered by LangChain & Gemini • 
        <a href="https://github.com" style="color: #667eea; text-decoration: none;">View Source</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
