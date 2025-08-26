from flask import Flask, render_template, request, jsonify, session, send_file, Response, redirect, url_for, flash
import uuid
import logging
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
import io
import csv
from functools import wraps

from config import Config
from models import db, User, Conversation, UserSession, Document, Analytics, FAQ, UserPreference
from database import DatabaseManager
from chatbot_brain import ChatbotBrain

# Add these imports to your existing app.py
from werkzeug.utils import secure_filename
import base64
from document_processor import DocumentProcessor

# Add this after your existing imports and before the app initialization
document_processor = DocumentProcessor()

# Create necessary directories
os.makedirs('database', exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('static/images', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=Config.LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize components
db_manager = DatabaseManager()
chatbot_brain = ChatbotBrain()

# Create tables
with app.app_context():
    db.create_all()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication helper functions
def hash_password(password):
    """Hash password with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, hashed_password):
    """Verify password against hash"""
    try:
        salt, password_hash = hashed_password.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except ValueError:
        return False

def create_user(username, email, password, is_admin=False):
    """Create new user in database"""
    try:
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return False, "User already exists"
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)
        
        new_user = User(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            is_admin=is_admin
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return True, user_id
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating user: {str(e)}")
        return False, "Error creating user"

def authenticate_user(username, password):
    """Authenticate user credentials"""
    try:
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and verify_password(password, user.password_hash):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        return None
        
    except Exception as e:
        logging.error(f"Error authenticating user: {str(e)}")
        return None

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        user = authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            logging.info(f"User logged in: {username}")
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields.', 'error')
            return render_template('auth/register.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        # Create user
        success, result = create_user(username, email, password)
        if success:
            flash('Registration successful! Please log in.', 'success')
            logging.info(f"New user registered: {username}")
            return redirect(url_for('login'))
        else:
            flash(result, 'error')
    
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    flash('You have been logged out successfully.', 'info')
    logging.info(f"User logged out: {username}")
    return redirect(url_for('login'))

# Protected routes
@app.route('/')
@login_required
def index():
    """Main chatbot interface"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard"""
    analytics_data = db_manager.get_analytics_data()
    return render_template('analytics.html', data=analytics_data)

@app.route('/admin')
@admin_required
def admin():
    """Admin panel"""
    analytics_data = db_manager.get_analytics_data()
    recent_conversations = get_recent_conversations_for_admin()
    recent_logs = get_recent_logs()
    
    admin_data = {
        'analytics': analytics_data,
        'recent_conversations': recent_conversations,
        'recent_logs': recent_logs,
        'system_status': get_system_status()
    }
    
    return render_template('admin.html', data=admin_data)

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

# API Routes (protected)
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages with document context support"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Get conversation history
        conversation_history = db_manager.get_conversation_history(session_id, limit=5)
        
        # Process message with document context support
        response_data = chatbot_brain.process_message(
            user_message, 
            session_id, 
            conversation_history
        )
        
        # Save conversation with user ID
        sentiment_score = None
        if response_data.get('sentiment'):
            sentiment_score = response_data['sentiment']['polarity']
        
        db_manager.save_conversation(
            session_id,
            user_message,
            response_data['message'],
            sentiment_score,
            response_data['intent'],
            session.get('user_id')
        )
        
        # Log interaction
        logging.info(f"Chat - User: {session.get('username')}, Session: {session_id}, Intent: {response_data['intent']}, Has Document: {response_data.get('has_document_context', False)}")
        
        return jsonify({
            'response': response_data['message'],
            'intent': response_data['intent'],
            'sentiment': response_data.get('sentiment', {}),
            'timestamp': response_data['timestamp'],
            'has_document_context': response_data.get('has_document_context', False),
            'source': response_data.get('source', 'ai_generated')
        })
        
    except Exception as e:
        logging.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'Sorry, I encountered an error. Please try again.',
            'response': 'I apologize, but I\'m having technical difficulties. Please try again in a moment.'
        }), 500

@app.route('/api/history')
@login_required
def get_history():
    """Get conversation history"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify([])
    
    history = db_manager.get_conversation_history(session_id, limit=20)
    
    formatted_history = []
    for msg in history:
        formatted_history.append({
            'user_message': msg[0],
            'bot_response': msg[1],
            'timestamp': msg[2]
        })
    
    return jsonify(formatted_history)

@app.route('/api/analytics')
@login_required
def get_analytics():
    """Get analytics data"""
    analytics_data = db_manager.get_analytics_data()
    return jsonify(analytics_data)

@app.route('/api/clear_session', methods=['POST'])
@login_required
def clear_session():
    """Clear current session"""
    old_session_id = session.get('session_id')
    session['session_id'] = str(uuid.uuid4())
    
    logging.info(f"Session cleared for user: {session.get('username')}, old session: {old_session_id}")
    return jsonify({'status': 'Session cleared'})

# Admin API Routes (protected)
@app.route('/api/admin/clear-sessions', methods=['POST'])
@admin_required
def admin_clear_sessions():
    """Clear all user sessions (Admin only)"""
    try:
        UserSession.query.delete()
        db.session.commit()
        
        logging.info(f"Admin {session.get('username')}: All sessions cleared")
        return jsonify({'status': 'All sessions cleared successfully'})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error clearing sessions: {str(e)}")
        return jsonify({'error': 'Failed to clear sessions'}), 500

@app.route('/api/admin/backup')
@admin_required
def admin_backup():
    """Backup database (Admin only)"""
    try:
        backup_filename = f"chatbot-backup-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Export all data as JSON
        backup_data = {
            'users': [user.to_dict() for user in User.query.all()],
            'conversations': [conv.to_dict() for conv in Conversation.query.all()],
            'sessions': [session.to_dict() for session in UserSession.query.all()],
            'documents': [doc.to_dict() for doc in Document.query.all()],
            'analytics': [anal.to_dict() for anal in Analytics.query.all()],
            'faq': [faq.to_dict() for faq in FAQ.query.all()],
            'preferences': [pref.to_dict() for pref in UserPreference.query.all()],
            'backup_date': datetime.now().isoformat()
        }
        
        # Create JSON response
        json_data = json.dumps(backup_data, indent=2, default=str)
        
        logging.info(f"Admin {session.get('username')}: Database backup created - {backup_filename}")
        
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={backup_filename}'}
        )
    except Exception as e:
        logging.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': 'Failed to create backup'}), 500

@app.route('/api/admin/restart-ai', methods=['POST'])
@admin_required
def admin_restart_ai():
    """Restart AI model (Admin only)"""
    try:
        global chatbot_brain
        chatbot_brain = ChatbotBrain()
        
        logging.info(f"Admin {session.get('username')}: AI model restarted")
        return jsonify({'status': 'AI model restarted successfully'})
    except Exception as e:
        logging.error(f"Error restarting AI: {str(e)}")
        return jsonify({'error': 'Failed to restart AI model'}), 500

@app.route('/api/admin/export-conversations')
@admin_required
def admin_export_conversations():
    """Export conversations as CSV (Admin only)"""
    try:
        conversations = db.session.query(Conversation, User.username)\
            .outerjoin(User, Conversation.user_id == User.id)\
            .order_by(Conversation.timestamp.desc())\
            .all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Session ID', 'User Message', 'Bot Response', 'Sentiment', 'Intent', 'Timestamp', 'Username'])
        
        for conv, username in conversations:
            writer.writerow([
                conv.session_id, 
                conv.user_message, 
                conv.bot_response, 
                conv.sentiment, 
                conv.intent, 
                conv.timestamp.isoformat() if conv.timestamp else '',
                username or 'Anonymous'
            ])
        
        output.seek(0)
        csv_data = output.getvalue()
        output.close()
        
        filename = f"conversations-{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logging.info(f"Admin {session.get('username')}: Conversations exported - {filename}")
        
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        logging.error(f"Error exporting conversations: {str(e)}")
        return jsonify({'error': 'Failed to export conversations'}), 500

# Helper functions
def get_recent_conversations_for_admin(limit=10):
    """Get recent conversations for admin panel"""
    try:
        conversations = db.session.query(Conversation, User.username)\
            .outerjoin(User, Conversation.user_id == User.id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'session_id': conv.session_id,
                'user_message': conv.user_message[:50] + ('...' if len(conv.user_message) > 50 else ''),
                'bot_response': conv.bot_response[:50] + ('...' if len(conv.bot_response) > 50 else ''),
                'intent': conv.intent,
                'sentiment': conv.sentiment,
                'timestamp': conv.timestamp.isoformat() if conv.timestamp else '',
                'username': username or 'Anonymous'
            }
            for conv, username in conversations
        ]
    except Exception as e:
        logging.error(f"Error getting recent conversations: {str(e)}")
        return []

def get_recent_logs(limit=50):
    """Get recent system logs"""
    try:
        if not os.path.exists(Config.LOG_FILE):
            return []
        
        with open(Config.LOG_FILE, 'r') as f:
            lines = f.readlines()
        
        recent_lines = lines[-limit:] if len(lines) > limit else lines
        return [line.strip() for line in recent_lines if line.strip()]
    except Exception as e:
        logging.error(f"Error reading logs: {str(e)}")
        return []

def get_system_status():
    """Get current system status"""
    try:
        db_status = 'Connected'
        try:
            db.session.execute('SELECT 1')
        except:
            db_status = 'Disconnected'
        
        ai_status = 'Active'
        try:
            if chatbot_brain and chatbot_brain.model:
                ai_status = 'Active'
            else:
                ai_status = 'Inactive'
        except:
            ai_status = 'Error'
        
        return {
            'server': 'Online',
            'database': db_status,
            'ai_model': ai_status,
            'uptime': '24h 15m'
        }
    except Exception as e:
        logging.error(f"Error getting system status: {str(e)}")
        return {
            'server': 'Online',
            'database': 'Unknown',
            'ai_model': 'Unknown',
            'uptime': 'Unknown'
        }

# User-specific API routes
@app.route('/api/user/stats')
@login_required
def get_user_stats():
    """Get user-specific statistics"""
    try:
        user_id = session.get('user_id')
        stats = db_manager.get_user_stats(user_id)
        
        # Add sessions today count
        today = datetime.utcnow().date()
        sessions_today = UserSession.query.filter(
            UserSession.user_id == user_id,
            db.func.date(UserSession.created_at) == today
        ).count()
        
        stats['sessions_today'] = sessions_today
        return jsonify(stats)
        
    except Exception as e:
        logging.error(f"Error getting user stats: {str(e)}")
        return jsonify({'error': 'Failed to get user stats'}), 500

@app.route('/api/user/export-data', methods=['POST'])
@login_required
def export_user_data():
    """Export user's data"""
    try:
        user_id = session.get('user_id')
        
        # Get user conversations
        conversations = db_manager.get_user_conversations(user_id, limit=1000)
        
        # Get user preferences
        preferences = db_manager.get_user_preferences(user_id)
        
        # Get user info
        user = User.query.get(user_id)
        
        # Prepare export data
        export_data = {
            'user_info': {
                'username': user.username if user else None,
                'email': user.email if user else None,
                'created_at': user.created_at.isoformat() if user and user.created_at else None,
                'export_date': datetime.now().isoformat()
            },
            'preferences': preferences,
            'conversations': [
                {
                    'session_id': conv[0],
                    'user_message': conv[1],
                    'bot_response': conv[2],
                    'timestamp': conv[3],
                    'sentiment': conv[4],
                    'intent': conv[5]
                }
                for conv in conversations
            ],
            'statistics': db_manager.get_user_stats(user_id)
        }
        
        # Create JSON response
        json_data = json.dumps(export_data, indent=2, default=str)
        
        filename = f"chatbot-data-{session.get('username', 'user')}-{datetime.now().strftime('%Y%m%d')}.json"
        
        logging.info(f"User {session.get('username')} exported their data")
        
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        logging.error(f"Error exporting user data: {str(e)}")
        return jsonify({'error': 'Failed to export data'}), 500

@app.route('/api/user/clear-history', methods=['POST'])
@login_required
def clear_user_history():
    """Clear user's chat history"""
    try:
        user_id = session.get('user_id')
        
        # Delete user's conversations
        Conversation.query.filter_by(user_id=user_id).delete()
        
        # Delete user's sessions
        UserSession.query.filter_by(user_id=user_id).delete()
        
        db.session.commit()
        
        # Clear current session
        session.pop('session_id', None)
        
        logging.info(f"User {session.get('username')} cleared their chat history")
        return jsonify({'success': True, 'message': 'Chat history cleared successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error clearing user history: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to clear history'}), 500

@app.route('/api/user/preferences', methods=['GET', 'POST'])
@login_required
def user_preferences():
    """Get or update user preferences"""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        try:
            preferences = db_manager.get_user_preferences(user_id)
            return jsonify(preferences)
        except Exception as e:
            logging.error(f"Error getting user preferences: {str(e)}")
            return jsonify({'error': 'Failed to get preferences'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            for key, value in data.items():
                db_manager.save_user_preference(user_id, key, str(value))
            
            logging.info(f"User {session.get('username')} updated preferences")
            return jsonify({'success': True, 'message': 'Preferences saved successfully'})
            
        except Exception as e:
            logging.error(f"Error saving user preferences: {str(e)}")
            return jsonify({'success': False, 'message': 'Failed to save preferences'}), 500

@app.route('/api/user/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'New password must be at least 6 characters'}), 400
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user or not verify_password(current_password, user.password_hash):
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Update password
        user.password_hash = hash_password(new_password)
        db.session.commit()
        
        logging.info(f"User {session.get('username')} changed password")
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error changing password: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to change password'}), 500

# Enhanced admin routes
@app.route('/api/admin/users')
@admin_required
def admin_get_users():
    """Get all users (Admin only)"""
    try:
        users = db.session.query(
            User,
            db.func.count(Conversation.id).label('message_count'),
            db.func.max(Conversation.timestamp).label('last_message')
        ).outerjoin(Conversation, User.id == Conversation.user_id)\
         .group_by(User.id)\
         .order_by(User.created_at.desc())\
         .all()
        
        formatted_users = []
        for user, message_count, last_message in users:
            formatted_users.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'message_count': message_count or 0,
                'last_message': last_message.isoformat() if last_message else None
            })
        
        return jsonify(formatted_users)
        
    except Exception as e:
        logging.error(f"Error getting users: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500

@app.route('/api/admin/users/<user_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(user_id):
    """Toggle user active status (Admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Toggle status
        user.is_active = not user.is_active
        db.session.commit()
        
        logging.info(f"Admin {session.get('username')}: Toggled user {user_id} status to {user.is_active}")
        return jsonify({'success': True, 'new_status': user.is_active})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling user status: {str(e)}")
        return jsonify({'error': 'Failed to toggle user status'}), 500

@app.route('/api/admin/users/<user_id>/make-admin', methods=['POST'])
@admin_required
def admin_make_admin(user_id):
    """Make user admin (Admin only)"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_admin = True
        db.session.commit()
        
        logging.info(f"Admin {session.get('username')}: Made user {user_id} an admin")
        return jsonify({'success': True, 'message': 'User promoted to admin'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error making user admin: {str(e)}")
        return jsonify({'error': 'Failed to make user admin'}), 500

@app.route('/user/history')
@login_required
def user_history():
    """User chat history page"""
    user_id = session.get('user_id')
    conversations = db_manager.get_user_conversations(user_id, limit=100)
    
    return render_template('user_history.html', conversations=conversations)

# Password reset routes (basic implementation)
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        # In a real implementation, you would:
        # 1. Check if email exists in database
        # 2. Generate a secure reset token
        # 3. Send reset email
        # 4. Store token with expiration
        
        flash('If an account with that email exists, you will receive password reset instructions.', 'info')
        return redirect(url_for('login'))
    
    return render_template('auth/forgot_password.html')

@app.route('/api/user/info')
@login_required
def get_user_info():
    """Get user information"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if user:
            return jsonify({
                'username': user.username,
                'email': user.email,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_admin': user.is_admin
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        logging.error(f"Error getting user info: {str(e)}")
        return jsonify({'error': 'Failed to get user info'}), 500

@app.route('/api/user/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not email:
            return jsonify({'success': False, 'message': 'Username and email are required'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters'}), 400
        
        # Validate email format
        import re
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        # Check if username/email already exists for other users
        existing_user = User.query.filter(
            ((User.username == username) | (User.email == email)) & 
            (User.id != user_id)
        ).first()
        
        if existing_user:
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 400
        
        # Update user info
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        user.username = username
        user.email = email
        db.session.commit()
        
        # Update session
        session['username'] = username
        
        logging.info(f"User {user_id} updated profile")
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update profile'}), 500

@app.route('/api/user/activity')
@login_required
def get_user_activity():
    """Get user's recent activity"""
    try:
        user_id = session.get('user_id')
        
        # Get recent conversations
        conversations = Conversation.query.filter_by(user_id=user_id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(10)\
            .all()
        
        activities = []
        for conv in conversations:
            timestamp = conv.timestamp
            intent = conv.intent or 'general'
            
            # Calculate time ago
            try:
                time_diff = datetime.utcnow() - timestamp
                
                if time_diff.days > 0:
                    time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    time_ago = "Just now"
            except:
                time_ago = "Unknown"
            
            # Determine activity description and icon
            if intent == 'greeting':
                description = "Started new chat session"
                icon = "fas fa-message"
                color = "blue"
            elif intent == 'question':
                description = "Asked a question"
                icon = "fas fa-question"
                color = "purple"
            elif intent == 'help_request':
                description = "Requested assistance"
                icon = "fas fa-hand-paper"
                color = "orange"
            else:
                description = "Sent a message"
                icon = "fas fa-comment"
                color = "green"
            
            activities.append({
                'description': description,
                'time_ago': time_ago,
                'icon': icon,
                'color': color
            })
        
        return jsonify(activities)
        
    except Exception as e:
        logging.error(f"Error getting user activity: {str(e)}")
        return jsonify([])

# Document upload routes
@app.route('/api/upload-document', methods=['POST'])
@login_required
def upload_document():
    """Handle document upload"""
    try:
        data = request.get_json()
        
        if not data or 'file_data' not in data or 'filename' not in data:
            return jsonify({'error': 'Missing file data or filename'}), 400
        
        # Decode base64 file data
        try:
            file_data = base64.b64decode(data['file_data'])
        except Exception as e:
            return jsonify({'error': 'Invalid file data format'}), 400
        
        filename = secure_filename(data['filename'])
        user_id = session.get('user_id')
        session_id = session.get('session_id')
        
        # Validate file
        errors, file_type = document_processor.validate_file(file_data, filename)
        if errors:
            return jsonify({'error': '; '.join(errors)}), 400
        
        # Save uploaded file
        file_info = document_processor.save_uploaded_file(file_data, filename, user_id)
        
        # Process document
        processing_result = document_processor.process_document(file_info)
        
        if not processing_result['success']:
            return jsonify({'error': processing_result['error']}), 400
        
        # Set document context in chatbot brain
        bot_response = chatbot_brain.process_document_upload(
            session_id,
            processing_result['content'],
            processing_result.get('summary'),
            filename
        )
        
        # Save the upload event to conversation history
        db_manager.save_conversation(
            session_id,
            f"[Document uploaded: {filename}]",
            bot_response['message'],
            None,
            'document_upload',
            user_id
        )
        
        # Save document info to database
        save_document_info(user_id, session_id, file_info, processing_result)
        
        logging.info(f"Document uploaded - User: {session.get('username')}, File: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded and processed successfully',
            'file_info': {
                'filename': filename,
                'file_type': file_type,
                'size': file_info['file_size'],
                'word_count': processing_result['metadata']['word_count']
            },
            'bot_response': bot_response
        })
        
    except Exception as e:
        logging.error(f"Error uploading document: {str(e)}")
        return jsonify({'error': 'Failed to upload document'}), 500

@app.route('/api/document-info')
@login_required
def get_document_info():
    """Get information about uploaded document in current session"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'has_document': False})
        
        doc_info = chatbot_brain.get_document_info(session_id)
        return jsonify(doc_info)
        
    except Exception as e:
        logging.error(f"Error getting document info: {str(e)}")
        return jsonify({'has_document': False})

@app.route('/api/clear-document', methods=['POST'])
@login_required
def clear_document():
    """Clear document context from current session"""
    try:
        session_id = session.get('session_id')
        if session_id:
            chatbot_brain.clear_document_context(session_id)
        
        return jsonify({'success': True, 'message': 'Document context cleared'})
        
    except Exception as e:
        logging.error(f"Error clearing document context: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to clear document context'})

@app.route('/api/supported-formats')
@login_required
def get_supported_formats():
    """Get list of supported file formats"""
    return jsonify({
        'formats': document_processor.supported_formats,
        'max_file_size_mb': document_processor.max_file_size // 1024 // 1024
    })

# Helper function to save document information to database
def save_document_info(user_id, session_id, file_info, processing_result):
    """Save document information to database"""
    try:
        document = Document(
            user_id=user_id,
            session_id=session_id,
            file_id=file_info['file_id'],
            original_filename=file_info['original_filename'],
            file_size=file_info['file_size'],
            file_type=processing_result['metadata'].get('file_type', 'unknown'),
            word_count=processing_result['metadata'].get('word_count', 0),
            char_count=processing_result['metadata'].get('char_count', 0),
            processed=processing_result['success']
        )
        
        db.session.add(document)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving document info: {str(e)}")

@app.route('/api/user/documents')
@login_required
def get_user_documents():
    """Get user's uploaded documents"""
    try:
        user_id = session.get('user_id')
        
        documents = Document.query.filter_by(user_id=user_id)\
            .order_by(Document.uploaded_at.desc())\
            .limit(20)\
            .all()
        
        formatted_documents = []
        for doc in documents:
            formatted_documents.append({
                'filename': doc.original_filename,
                'file_size': doc.file_size,
                'word_count': doc.word_count,
                'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                'processed': doc.processed
            })
        
        return jsonify(formatted_documents)
        
    except Exception as e:
        logging.error(f"Error getting user documents: {str(e)}")
        return jsonify([])

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Database initialization
def init_db():
    """Initialize database with default data"""
    try:
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            success, result = create_user('admin', 'admin@example.com', 'admin123', is_admin=True)
            if success:
                logging.info("Default admin user created: admin/admin123")
            else:
                logging.error(f"Failed to create admin user: {result}")
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")

# Application startup
if __name__ == '__main__':
    with app.app_context():
        init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5001)