import google.generativeai as genai
import json
import re
from datetime import datetime
from config import Config
from sentiment_analyzer import SentimentAnalyzer

class ChatbotBrain:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # Document context storage
        self.document_contexts = {}  # session_id -> document_content
        
        # Predefined responses for common queries
        self.predefined_responses = {
            'greeting': [
                "Hello! I'm your AI assistant. I can help you with various tasks and also analyze documents you upload. How can I help you today?",
                "Hi there! What can I do for you? Feel free to upload documents for analysis too!",
                "Welcome! I'm here to assist you with any questions, tasks, or document analysis."
            ],
            'goodbye': [
                "Goodbye! Feel free to come back anytime you need assistance.",
                "See you later! Have a great day!",
                "Thanks for chatting with me. Take care!"
            ],
            'thanks': [
                "You're welcome! Is there anything else I can help you with?",
                "Happy to help! Let me know if you need anything else.",
                "Glad I could assist you!"
            ],
            'document_uploaded': [
                "Great! I've processed your document. You can now ask me questions about its content.",
                "Document uploaded and analyzed successfully! What would you like to know about it?",
                "Your document is ready for analysis. Feel free to ask questions about its content."
            ]
        }
        
        self.system_prompt = """
        You are a helpful, intelligent AI assistant chatbot with document analysis capabilities. You should:
        1. Be friendly, professional, and conversational
        2. Provide accurate and helpful information
        3. Ask clarifying questions when needed
        4. Keep responses concise but comprehensive
        5. Show empathy and understanding
        6. Handle various topics including general knowledge, technical questions, creative tasks, etc.
        7. When analyzing documents, reference specific parts of the content in your responses
        8. If you don't know something, admit it honestly
        9. Always aim to be helpful while being truthful
        10. When a document is provided, prioritize information from that document in your responses
        11. Clearly indicate when you're referencing uploaded document content vs. general knowledge
        """
    
    def set_document_context(self, session_id, document_content, document_summary=None):
        """Set document context for a session"""
        self.document_contexts[session_id] = {
            'content': document_content,
            'summary': document_summary,
            'uploaded_at': datetime.now().isoformat()
        }
    
    def get_document_context(self, session_id):
        """Get document context for a session"""
        return self.document_contexts.get(session_id)
    
    def clear_document_context(self, session_id):
        """Clear document context for a session"""
        if session_id in self.document_contexts:
            del self.document_contexts[session_id]
    
    def detect_intent(self, message):
        """Detect user intent from message"""
        message_lower = message.lower()
        
        # Document-related intents
        if any(word in message_lower for word in ['document', 'file', 'upload', 'pdf', 'analyze']):
            return 'document_query'
        elif any(word in message_lower for word in ['summarize', 'summary', 'what does', 'explain this']):
            return 'document_analysis'
        
        # Simple intent detection based on keywords
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
            return 'greeting'
        elif any(word in message_lower for word in ['bye', 'goodbye', 'see you', 'farewell']):
            return 'goodbye'
        elif any(word in message_lower for word in ['thank', 'thanks', 'appreciate']):
            return 'thanks'
        elif any(word in message_lower for word in ['help', 'support', 'assist']):
            return 'help_request'
        elif '?' in message:
            return 'question'
        else:
            return 'general'
    
    def get_predefined_response(self, intent):
        """Get predefined response for specific intents"""
        if intent in self.predefined_responses:
            import random
            return random.choice(self.predefined_responses[intent])
        return None
    
    def generate_response(self, user_message, session_id, conversation_history=None, sentiment_data=None):
        """Generate AI response using Gemini with document context"""
        try:
            # Detect intent
            intent = self.detect_intent(user_message)
            
            # Check for predefined responses first (but not for document queries)
            if intent not in ['document_query', 'document_analysis']:
                predefined_response = self.get_predefined_response(intent)
                if predefined_response and intent in ['greeting', 'goodbye', 'thanks']:
                    return {
                        'response': predefined_response,
                        'intent': intent,
                        'source': 'predefined'
                    }
            
            # Prepare context for AI
            context = self.system_prompt
            
            # Add document context if available
            document_context = self.get_document_context(session_id)
            if document_context:
                context += f"\n\nDOCUMENT CONTEXT AVAILABLE:\n"
                context += f"Document uploaded at: {document_context['uploaded_at']}\n"
                
                if document_context.get('summary'):
                    context += f"Document Summary: {document_context['summary']}\n"
                
                # Truncate document content if too long (keep first and last parts)
                content = document_context['content']
                if len(content) > 8000:  # Truncate if too long
                    content = content[:4000] + "\n\n[... content truncated ...]\n\n" + content[-4000:]
                
                context += f"Document Content:\n{content}\n"
                context += "\nIMPORTANT: When answering questions, prioritize information from the document context above. Always indicate when you're referencing the uploaded document.\n"
            
            # Add conversation history
            if conversation_history:
                context += "\n\nPrevious conversation context:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages
                    context += f"User: {msg[0]}\nAssistant: {msg[1]}\n"
            
            # Add sentiment context
            if sentiment_data and Config.ENABLE_SENTIMENT_ANALYSIS:
                sentiment_modifier = self.sentiment_analyzer.get_emotion_response_modifier(sentiment_data)
                if sentiment_modifier:
                    context += f"\n\nNote: {sentiment_modifier}"
            
            # Enhance prompt based on intent
            if intent in ['document_query', 'document_analysis'] and document_context:
                context += f"\n\nThe user is asking about the uploaded document. Please provide a detailed response based on the document content."
            elif intent == 'document_query' and not document_context:
                return {
                    'response': "I don't see any uploaded document in our current session. Please upload a document first, and then I can help you analyze it or answer questions about its content.",
                    'intent': intent,
                    'source': 'no_document'
                }
            
            # Generate response using Gemini
            full_prompt = f"{context}\n\nCurrent user message: {user_message}\n\nResponse:"
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=Config.DEFAULT_RESPONSE_TEMPERATURE,
                    max_output_tokens=800,  # Increased for document analysis
                )
            )
            
            # Post-process response to add document indicators
            response_text = response.text.strip()
            if document_context and any(keyword in user_message.lower() for keyword in ['document', 'file', 'uploaded', 'text']):
                # Add indicator that response is based on document
                if not any(indicator in response_text.lower() for indicator in ['based on', 'according to', 'from the document']):
                    response_text = f"Based on your uploaded document: {response_text}"
            
            return {
                'response': response_text,
                'intent': intent,
                'source': 'ai_generated',
                'has_document_context': document_context is not None
            }
            
        except Exception as e:
            return {
                'response': f"I apologize, but I'm experiencing some technical difficulties. Could you please try again? Error: {str(e)}",
                'intent': 'error',
                'source': 'error_handler'
            }
    
    def process_message(self, user_message, session_id, conversation_history=None):
        """Process user message and return response"""
        # Analyze sentiment
        sentiment_data = None
        if Config.ENABLE_SENTIMENT_ANALYSIS:
            sentiment_data = self.sentiment_analyzer.analyze_sentiment(user_message)
        
        # Generate response
        response_data = self.generate_response(
            user_message, 
            session_id,
            conversation_history, 
            sentiment_data
        )
        
        return {
            'message': response_data['response'],
            'intent': response_data['intent'],
            'sentiment': sentiment_data,
            'timestamp': datetime.now().isoformat(),
            'source': response_data['source'],
            'has_document_context': response_data.get('has_document_context', False)
        }
    
    def process_document_upload(self, session_id, document_content, document_summary=None, filename=None):
        """Process a document upload and provide initial response"""
        try:
            # Set document context
            self.set_document_context(session_id, document_content, document_summary)
            
            # Generate initial response about the document
            if document_summary:
                summary_text = f"Document '{filename}' processed successfully!\n\n"
                summary_text += f"📄 **Document Summary:**\n"
                summary_text += f"- Word count: {document_summary.get('word_count', 'N/A')}\n"
                summary_text += f"- Lines: {document_summary.get('non_empty_lines', 'N/A')}\n"
                summary_text += f"- Characters: {document_summary.get('char_count', 'N/A')}\n\n"
                
                if document_summary.get('first_few_lines'):
                    summary_text += "📝 **Content Preview:**\n"
                    for i, line in enumerate(document_summary['first_few_lines'][:3], 1):
                        summary_text += f"{i}. {line[:100]}{'...' if len(line) > 100 else ''}\n"
                
                summary_text += "\n✨ **You can now ask me questions about this document!**\n"
                summary_text += "Try asking things like:\n"
                summary_text += "• 'What is this document about?'\n"
                summary_text += "• 'Summarize the main points'\n"
                summary_text += "• 'Find information about [topic]'\n"
            else:
                summary_text = f"Document '{filename}' uploaded and processed! You can now ask me questions about its content."
            
            return {
                'message': summary_text,
                'intent': 'document_uploaded',
                'sentiment': None,
                'timestamp': datetime.now().isoformat(),
                'source': 'document_processor',
                'has_document_context': True
            }
            
        except Exception as e:
            return {
                'message': f"Sorry, there was an error processing your document: {str(e)}",
                'intent': 'error',
                'sentiment': None,
                'timestamp': datetime.now().isoformat(),
                'source': 'error_handler',
                'has_document_context': False
            }
    
    def get_document_info(self, session_id):
        """Get information about uploaded document"""
        context = self.get_document_context(session_id)
        if context:
            return {
                'has_document': True,
                'uploaded_at': context['uploaded_at'],
                'summary': context.get('summary'),
                'content_length': len(context['content'])
            }
        return {'has_document': False}