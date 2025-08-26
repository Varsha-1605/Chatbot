from textblob import TextBlob
import nltk
try:
    nltk.download('punkt', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
except:
    pass

class SentimentAnalyzer:
    def __init__(self):
        pass
    
    def analyze_sentiment(self, text):
        """Analyze sentiment of text using TextBlob"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            # Convert polarity to sentiment label
            if polarity > 0.1:
                sentiment_label = "positive"
            elif polarity < -0.1:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"
            
            return {
                'polarity': polarity,
                'label': sentiment_label,
                'confidence': abs(polarity)
            }
        except Exception as e:
            return {
                'polarity': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def get_emotion_response_modifier(self, sentiment_data):
        """Get response modifier based on sentiment"""
        sentiment_label = sentiment_data.get('label', 'neutral')
        
        modifiers = {
            'positive': "I'm glad you seem positive! ",
            'negative': "I understand you might be feeling frustrated. Let me help you with that. ",
            'neutral': ""
        }
        
        return modifiers.get(sentiment_label, "")
