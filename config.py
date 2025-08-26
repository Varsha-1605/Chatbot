import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or 'your-gemini-api-key'
    
    # Database Configuration for SQLAlchemy
    # For local development with SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///chatbot.db'
    
    # Handle PostgreSQL URL for Render (if needed)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/chatbot.log')
    
    # Chatbot Settings
    MAX_CONVERSATION_HISTORY = 10
    DEFAULT_RESPONSE_TEMPERATURE = 0.7
    ENABLE_SENTIMENT_ANALYSIS = True
    ENABLE_ANALYTICS = True