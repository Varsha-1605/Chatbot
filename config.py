import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key'
    # DATABASE_PATH = 'database/chatbot.db'
    # LOG_FILE = 'logs/chatbot.log'
    # With these lines:
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database/chatbot.db')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/chatbot.log')
    
    # Chatbot Settings
    MAX_CONVERSATION_HISTORY = 10
    DEFAULT_RESPONSE_TEMPERATURE = 0.7
    ENABLE_SENTIMENT_ANALYSIS = True
    ENABLE_ANALYTICS = True