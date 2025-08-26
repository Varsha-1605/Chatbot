import sqlite3
import json
from datetime import datetime
from config import Config

class DatabaseManager:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Conversations table (updated with user_id)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                sentiment REAL,
                intent TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # FAQ table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faq (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                preference_key TEXT NOT NULL,
                preference_value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, preference_key)
            )
        ''')
        
        # Login attempts table (for security)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                ip_address TEXT,
                success BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create admin user if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            # Import the hash_password function locally to avoid circular imports
            import hashlib
            import secrets
            
            def hash_password(password):
                salt = secrets.token_hex(16)
                password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                return f"{salt}:{password_hash}"
            
            # Create default admin user
            admin_password_hash = hash_password('admin123')
            cursor.execute('''
                INSERT INTO users (id, username, email, password_hash, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin-001', 'admin', 'admin@chatbot.com', admin_password_hash, True))
            
            print("Default admin user created:")
            print("Username: admin")
            print("Password: admin123")
            print("Please change this password after first login!")
        
        conn.commit()
        conn.close()
    
    def save_conversation(self, session_id, user_message, bot_response, sentiment=None, intent=None, user_id=None):
        """Save conversation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (session_id, user_id, user_message, bot_response, sentiment, intent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, user_id, user_message, bot_response, sentiment, intent))
        
        # Update session info
        cursor.execute('''
            INSERT OR REPLACE INTO user_sessions (session_id, user_id, last_activity, message_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT message_count FROM user_sessions WHERE session_id = ?), 0) + 1)
        ''', (session_id, user_id, session_id))
        
        conn.commit()
        conn.close()
    
    def get_conversation_history(self, session_id, limit=10):
        """Get conversation history for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, bot_response, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return list(reversed(results))
    
    def get_user_conversations(self, user_id, limit=50):
        """Get all conversations for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_id, user_message, bot_response, timestamp, sentiment, intent
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_analytics_data(self):
        """Get analytics data for dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total conversations
        cursor.execute('SELECT COUNT(*) FROM conversations')
        total_conversations = cursor.fetchone()[0]
        
        # Unique users
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM conversations WHERE user_id IS NOT NULL')
        unique_users = cursor.fetchone()[0]
        
        # Registered users
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        registered_users = cursor.fetchone()[0]
        
        # Average sentiment
        cursor.execute('SELECT AVG(sentiment) FROM conversations WHERE sentiment IS NOT NULL')
        avg_sentiment = cursor.fetchone()[0] or 0
        
        # Messages per day (last 7 days)
        cursor.execute('''
            SELECT DATE(timestamp), COUNT(*)
            FROM conversations
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY DATE(timestamp)
        ''')
        messages_per_day = cursor.fetchall()
        
        # User activity stats
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT DATE(c.timestamp)) as active_days,
                AVG(daily_messages.msg_count) as avg_daily_messages
            FROM conversations c
            JOIN (
                SELECT DATE(timestamp) as date, COUNT(*) as msg_count
                FROM conversations 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY DATE(timestamp)
            ) daily_messages ON DATE(c.timestamp) = daily_messages.date
            WHERE c.timestamp >= datetime('now', '-30 days')
        ''')
        user_activity = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_conversations': total_conversations,
            'unique_users': unique_users,
            'registered_users': registered_users,
            'avg_sentiment': round(avg_sentiment, 2),
            'messages_per_day': messages_per_day,
            'active_days': user_activity[0] if user_activity[0] else 0,
            'avg_daily_messages': round(user_activity[1], 1) if user_activity[1] else 0
        }
    
    def log_login_attempt(self, username, ip_address, success):
        """Log login attempts for security monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO login_attempts (username, ip_address, success)
            VALUES (?, ?, ?)
        ''', (username, ip_address, success))
        
        conn.commit()
        conn.close()
    
    def get_failed_login_attempts(self, username, minutes=15):
        """Get failed login attempts for a username in the last N minutes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM login_attempts
            WHERE username = ? AND success = 0
            AND timestamp > datetime('now', '-{} minutes')
        '''.format(minutes), (username,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def update_last_login(self, user_id):
        """Update user's last login timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_preferences(self, user_id):
        """Get user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT preference_key, preference_value
            FROM user_preferences
            WHERE user_id = ?
        ''', (user_id,))
        
        preferences = dict(cursor.fetchall())
        conn.close()
        
        return preferences
    
    def save_user_preference(self, user_id, key, value):
        """Save or update user preference"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, key, value))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id):
        """Get statistics for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM conversations WHERE user_id = ?', (user_id,))
        total_messages = cursor.fetchone()[0]
        
        # Average sentiment
        cursor.execute('SELECT AVG(sentiment) FROM conversations WHERE user_id = ? AND sentiment IS NOT NULL', (user_id,))
        avg_sentiment = cursor.fetchone()[0] or 0
        
        # Most common intent
        cursor.execute('''
            SELECT intent, COUNT(*) as count
            FROM conversations
            WHERE user_id = ? AND intent IS NOT NULL
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 1
        ''', (user_id,))
        
        top_intent = cursor.fetchone()
        
        # First interaction
        cursor.execute('SELECT MIN(timestamp) FROM conversations WHERE user_id = ?', (user_id,))
        first_interaction = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_messages': total_messages,
            'avg_sentiment': round(avg_sentiment, 2),
            'top_intent': top_intent[0] if top_intent else 'None',
            'first_interaction': first_interaction
        }