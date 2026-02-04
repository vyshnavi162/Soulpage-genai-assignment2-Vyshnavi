"""
Configuration module for the Conversational Knowledge Bot.
Handles environment variables and default settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Model Configuration
MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE = 0.7
MAX_TOKENS = 2048

# Chat History Configuration
CHAT_HISTORY_DIR = "chat_history"
MAX_HISTORY_LENGTH = 50  # Maximum messages to keep in memory

# Bot Configuration
BOT_NAME = "Nova"
BOT_AVATAR = "🤖"
USER_AVATAR = "👤"

# Ensure chat history directory exists
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
