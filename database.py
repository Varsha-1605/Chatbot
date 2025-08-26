from datetime import datetime, timedelta
from sqlalchemy import func, text, and_
from models import db, User, Conversation, UserSession, Document, Analytics, FAQ, UserPreference

class DatabaseManager:
    def __init__(self):
        pass  # Database is now handled by Flask-SQLAlchemy
    
    def save_conversation(self, session_id, user_message, bot_response, sentiment=None, intent=None, user_id=None):
        """Save conversation to database"""
        try:
            conversation = Conversation(
                session_id=session_id,
                user_message=user_message,
                bot_response=bot_response,
                sentiment=sentiment,
                intent=intent,
                user_id=user_id
            )
            db.session.add(conversation)
            
            # Update or create session info
            session = UserSession.query.filter_by(session_id=session_id).first()
            if session:
                session.last_activity = datetime.utcnow()
                session.message_count += 1
            else:
                session = UserSession(
                    session_id=session_id,
                    user_id=user_id,
                    message_count=1
                )
                db.session.add(session)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_conversation_history(self, session_id, limit=10):
        """Get conversation history for a session"""
        conversations = Conversation.query.filter_by(session_id=session_id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(limit)\
            .all()
        
        # Return in chronological order (oldest first)
        return [(conv.user_message, conv.bot_response, conv.timestamp.isoformat()) 
                for conv in reversed(conversations)]
    
    def get_user_conversations(self, user_id, limit=100):
        """Get user's conversations"""
        conversations = Conversation.query.filter_by(user_id=user_id)\
            .order_by(Conversation.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [(conv.session_id, conv.user_message, conv.bot_response, 
                conv.timestamp.isoformat(), conv.sentiment, conv.intent) 
                for conv in conversations]
    
    def get_analytics_data(self):
        """Get analytics data for dashboard"""
        try:
            # Total conversations
            total_conversations = Conversation.query.count()
            
            # Unique users (sessions)
            unique_sessions = UserSession.query.count()
            
            # Average sentiment
            avg_sentiment = db.session.query(func.avg(Conversation.sentiment))\
                .filter(Conversation.sentiment.isnot(None))\
                .scalar() or 0
            
            # Messages per day (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            messages_per_day = db.session.query(
                func.date(Conversation.timestamp).label('date'),
                func.count(Conversation.id).label('count')
            )\
            .filter(Conversation.timestamp >= seven_days_ago)\
            .group_by(func.date(Conversation.timestamp))\
            .order_by(func.date(Conversation.timestamp))\
            .all()
            
            # Recent activity
            recent_activity = Conversation.query\
                .join(User, Conversation.user_id == User.id, isouter=True)\
                .order_by(Conversation.timestamp.desc())\
                .limit(5)\
                .all()
            
            # Intent distribution
            intent_distribution = db.session.query(
                Conversation.intent,
                func.count(Conversation.id).label('count')
            )\
            .filter(Conversation.intent.isnot(None))\
            .group_by(Conversation.intent)\
            .order_by(func.count(Conversation.id).desc())\
            .limit(10)\
            .all()
            
            return {
                'total_conversations': total_conversations,
                'unique_users': unique_sessions,
                'avg_sentiment': round(avg_sentiment, 2),
                'messages_per_day': [(str(date), count) for date, count in messages_per_day],
                'recent_activity': [
                    {
                        'user_message': conv.user_message[:50] + ('...' if len(conv.user_message) > 50 else ''),
                        'bot_response': conv.bot_response[:50] + ('...' if len(conv.bot_response) > 50 else ''),
                        'timestamp': conv.timestamp.isoformat(),
                        'username': conv.user.username if conv.user else 'Anonymous'
                    }
                    for conv in recent_activity
                ],
                'intent_distribution': [{'intent': intent, 'count': count} 
                                      for intent, count in intent_distribution]
            }
        except Exception as e:
            print(f"Error getting analytics: {str(e)}")
            return {
                'total_conversations': 0,
                'unique_users': 0,
                'avg_sentiment': 0,
                'messages_per_day': [],
                'recent_activity': [],
                'intent_distribution': []
            }
    
    def get_user_stats(self, user_id):
        """Get user-specific statistics"""
        try:
            # Total messages
            total_messages = Conversation.query.filter_by(user_id=user_id).count()
            
            # Sessions count
            sessions_count = UserSession.query.filter_by(user_id=user_id).count()
            
            # Average sentiment
            avg_sentiment = db.session.query(func.avg(Conversation.sentiment))\
                .filter(and_(Conversation.user_id == user_id, 
                           Conversation.sentiment.isnot(None)))\
                .scalar() or 0
            
            # Most used intents
            top_intents = db.session.query(
                Conversation.intent,
                func.count(Conversation.id).label('count')
            )\
            .filter(and_(Conversation.user_id == user_id, 
                        Conversation.intent.isnot(None)))\
            .group_by(Conversation.intent)\
            .order_by(func.count(Conversation.id).desc())\
            .limit(5)\
            .all()
            
            # Documents uploaded
            documents_count = Document.query.filter_by(user_id=user_id).count()
            
            return {
                'total_messages': total_messages,
                'sessions_count': sessions_count,
                'avg_sentiment': round(avg_sentiment, 2),
                'top_intents': [{'intent': intent, 'count': count} 
                               for intent, count in top_intents],
                'documents_uploaded': documents_count
            }
        except Exception as e:
            print(f"Error getting user stats: {str(e)}")
            return {
                'total_messages': 0,
                'sessions_count': 0,
                'avg_sentiment': 0,
                'top_intents': [],
                'documents_uploaded': 0
            }
    
    def save_user_preference(self, user_id, preference_key, preference_value):
        """Save user preference"""
        try:
            preference = UserPreference.query.filter_by(
                user_id=user_id, 
                preference_key=preference_key
            ).first()
            
            if preference:
                preference.preference_value = preference_value
                preference.updated_at = datetime.utcnow()
            else:
                preference = UserPreference(
                    user_id=user_id,
                    preference_key=preference_key,
                    preference_value=preference_value
                )
                db.session.add(preference)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def get_user_preferences(self, user_id):
        """Get user preferences"""
        try:
            preferences = UserPreference.query.filter_by(user_id=user_id).all()
            return {pref.preference_key: pref.preference_value for pref in preferences}
        except Exception as e:
            print(f"Error getting preferences: {str(e)}")
            return {}
    
    def clear_user_data(self, user_id):
        """Clear all user data"""
        try:
            # Delete conversations
            Conversation.query.filter_by(user_id=user_id).delete()
            
            # Delete sessions
            UserSession.query.filter_by(user_id=user_id).delete()
            
            # Delete documents
            Document.query.filter_by(user_id=user_id).delete()
            
            # Delete preferences
            UserPreference.query.filter_by(user_id=user_id).delete()
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def save_analytics_data(self, metric_name, metric_value, date=None):
        """Save analytics data"""
        try:
            analytics = Analytics(
                metric_name=metric_name,
                metric_value=str(metric_value),
                date=date or datetime.utcnow().date()
            )
            db.session.add(analytics)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    
    def add_faq(self, question, answer, category=None):
        """Add FAQ entry"""
        try:
            faq = FAQ(
                question=question,
                answer=answer,
                category=category
            )
            db.session.add(faq)
            db.session.commit()
            return faq.id
        except Exception as e:
            db.session.rollback()
            raise e
    
    def search_conversations(self, query, user_id=None, limit=50):
        """Search conversations by text"""
        try:
            filters = [
                Conversation.user_message.contains(query) |
                Conversation.bot_response.contains(query)
            ]
            
            if user_id:
                filters.append(Conversation.user_id == user_id)
            
            conversations = Conversation.query\
                .filter(and_(*filters))\
                .order_by(Conversation.timestamp.desc())\
                .limit(limit)\
                .all()
            
            return [conv.to_dict() for conv in conversations]
        except Exception as e:
            print(f"Error searching conversations: {str(e)}")
            return []
    
    def get_active_sessions(self, since_hours=24):
        """Get active sessions within specified hours"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
            sessions = UserSession.query\
                .filter(UserSession.last_activity >= cutoff_time)\
                .order_by(UserSession.last_activity.desc())\
                .all()
            
            return [session.to_dict() for session in sessions]
        except Exception as e:
            print(f"Error getting active sessions: {str(e)}")
            return []
    
    def cleanup_old_data(self, days_old=90):
        """Clean up old data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Clean old conversations from anonymous users
            old_conversations = Conversation.query\
                .filter(and_(
                    Conversation.timestamp < cutoff_date,
                    Conversation.user_id.is_(None)
                ))\
                .delete()
            
            # Clean old sessions
            old_sessions = UserSession.query\
                .filter(UserSession.last_activity < cutoff_date)\
                .delete()
            
            db.session.commit()
            
            return {
                'conversations_deleted': old_conversations,
                'sessions_deleted': old_sessions
            }
        except Exception as e:
            db.session.rollback()
            raise e