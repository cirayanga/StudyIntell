import logging
import base64
from io import BytesIO
from flask import Blueprint, request, jsonify, session, g
from app import db
from models import StudySession, Conversation, UserPreferences
from services.ai_service import AIService
from services.speech_service import SpeechService
from services.rag_service import RAGService
from middleware.rate_limiter import (
    rate_limit_assemblyai, rate_limit_google_tts, 
    rate_limit_cohere, rate_limit_general, circuit_breaker
)

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)

# Initialize services
ai_service = AIService()
speech_service = SpeechService()
rag_service = RAGService()

@api_bp.route('/transcribe', methods=['POST'])
@rate_limit_assemblyai
def transcribe_audio():
    """Transcribe audio to text using AssemblyAI"""
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Read audio data
        audio_data = audio_file.read()
        
        # Use circuit breaker for API call
        def transcribe_call():
            return speech_service.transcribe_audio(audio_data)
        
        result = circuit_breaker.call('assemblyai', transcribe_call)
        
        if result['success']:
            return jsonify({
                'text': result['text'],
                'confidence': result.get('confidence', 0.8),
                'duration': result.get('duration', 0),
                'success': True
            })
        else:
            return jsonify({
                'error': result.get('error', 'Transcription failed'),
                'success': False
            }), 500
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'error': 'Internal server error during transcription'}), 500

@api_bp.route('/synthesize', methods=['POST'])
@rate_limit_google_tts
def synthesize_speech():
    """Convert text to speech using Google TTS"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        voice_name = data.get('voice', 'en-US-Standard-A')
        speed = data.get('speed', 1.0)
        
        # Use circuit breaker for API call
        def tts_call():
            return speech_service.text_to_speech(text, voice_name, speed)
        
        result = circuit_breaker.call('google_tts', tts_call)
        
        if result['success']:
            return jsonify({
                'audio_data': result['audio_data'],
                'format': result['format'],
                'success': True
            })
        else:
            return jsonify({
                'error': result.get('error', 'Speech synthesis failed'),
                'success': False
            }), 500
            
    except Exception as e:
        logger.error(f"Speech synthesis error: {e}")
        return jsonify({'error': 'Internal server error during speech synthesis'}), 500

@api_bp.route('/chat', methods=['POST'])
@rate_limit_general
def chat():
    """Handle chat interactions with AI services"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
        
        user_message = data['message']
        session_id = data.get('session_id')
        input_method = data.get('input_method', 'text')
        
        if not session_id:
            return jsonify({'error': 'Session ID required'}), 400
        
        # Get study session
        study_session = StudySession.query.get(session_id)
        if not study_session:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        # Get conversation history for context
        recent_conversations = Conversation.query.filter_by(session_id=session_id)\
                                                .order_by(Conversation.timestamp.desc())\
                                                .limit(5).all()
        
        conversation_history = [
            {
                'user_input': conv.user_input,
                'ai_response': conv.ai_response
            }
            for conv in reversed(recent_conversations)
        ]
        
        # Get relevant context from knowledge base
        rag_context = rag_service.get_context_for_query(user_message)
        
        # Use circuit breaker for AI service calls
        def ai_call():
            return ai_service.get_study_response(
                user_message, 
                context=rag_context,
                conversation_history=conversation_history
            )
        
        ai_response = circuit_breaker.call('ai_service', ai_call)
        
        if ai_response['success']:
            # Save conversation to database
            conversation = Conversation(
                session_id=session_id,
                user_input=user_message,
                ai_response=ai_response['response'],
                input_method=input_method,
                audio_duration=data.get('audio_duration', 0)
            )
            db.session.add(conversation)
            
            # Update session stats
            study_session.total_interactions += 1
            
            db.session.commit()
            
            # Get study recommendations
            recommendations = rag_service.get_study_recommendations(user_message)
            
            return jsonify({
                'response': ai_response['response'],
                'source': ai_response['source'],
                'recommendations': recommendations,
                'context_used': bool(rag_context),
                'success': True
            })
        else:
            return jsonify({
                'error': 'AI service unavailable',
                'fallback_response': ai_response['response'],
                'success': False
            }), 503
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': 'Internal server error during chat'}), 500

@api_bp.route('/knowledge/search', methods=['POST'])
@rate_limit_general
def search_knowledge():
    """Search the knowledge base"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'No search query provided'}), 400
        
        query = data['query']
        limit = data.get('limit', 5)
        
        results = rag_service.search_knowledge(query, k=limit)
        
        return jsonify({
            'results': results,
            'query': query,
            'count': len(results),
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Knowledge search error: {e}")
        return jsonify({'error': 'Internal server error during search'}), 500

@api_bp.route('/knowledge/add', methods=['POST'])
@rate_limit_general
def add_knowledge():
    """Add new knowledge to the knowledge base"""
    try:
        data = request.get_json()
        required_fields = ['title', 'content', 'category']
        
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        title = data['title']
        content = data['content']
        category = data['category']
        source_url = data.get('source_url')
        
        success = rag_service.add_knowledge(title, content, category, source_url)
        
        if success:
            return jsonify({
                'message': 'Knowledge added successfully',
                'success': True
            })
        else:
            return jsonify({
                'error': 'Failed to add knowledge',
                'success': False
            }), 500
            
    except Exception as e:
        logger.error(f"Add knowledge error: {e}")
        return jsonify({'error': 'Internal server error while adding knowledge'}), 500

@api_bp.route('/session/<int:session_id>/summary', methods=['GET'])
@rate_limit_general
def get_session_summary(session_id):
    """Get a summary of a study session"""
    try:
        study_session = StudySession.query.get(session_id)
        if not study_session:
            return jsonify({'error': 'Session not found'}), 404
        
        conversations = Conversation.query.filter_by(session_id=session_id)\
                                        .order_by(Conversation.timestamp.asc()).all()
        
        conversation_data = [
            {
                'user_input': conv.user_input,
                'ai_response': conv.ai_response,
                'timestamp': conv.timestamp.isoformat()
            }
            for conv in conversations
        ]
        
        # Generate AI summary
        def summary_call():
            return ai_service.summarize_session(conversation_data)
        
        summary = circuit_breaker.call('ai_service', summary_call)
        
        return jsonify({
            'session_name': study_session.session_name,
            'total_interactions': study_session.total_interactions,
            'summary': summary,
            'conversation_count': len(conversations),
            'created_at': study_session.created_at.isoformat(),
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Session summary error: {e}")
        return jsonify({'error': 'Internal server error getting session summary'}), 500

@api_bp.route('/voices', methods=['GET'])
@rate_limit_general
def get_available_voices():
    """Get available TTS voices"""
    try:
        result = speech_service.get_available_voices()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Get voices error: {e}")
        return jsonify({
            'voices': [],
            'success': False,
            'error': 'Internal server error getting voices'
        }), 500

@api_bp.after_request
def after_request(response):
    """Add rate limit headers to API responses"""
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
    if hasattr(g, 'rate_limit_reset'):
        response.headers['X-RateLimit-Reset'] = str(int(g.rate_limit_reset))
    
    return response
