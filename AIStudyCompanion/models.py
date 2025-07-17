from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON

class StudySession(db.Model):
    __tablename__ = 'study_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_interactions = db.Column(db.Integer, default=0)
    
    # Relationship to conversations
    conversations = db.relationship('Conversation', backref='session', lazy=True, cascade='all, delete-orphan')

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('study_sessions.id'), nullable=False)
    user_input = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    input_method = db.Column(db.String(20), nullable=False)  # 'voice' or 'text'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    audio_duration = db.Column(db.Float)  # Duration in seconds for voice inputs
    
class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_base'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    embeddings = db.Column(JSON)  # Store vector embeddings as JSON
    source_url = db.Column(db.String(500))
    
class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)  # Browser session ID
    voice_enabled = db.Column(db.Boolean, default=True)
    speech_rate = db.Column(db.Float, default=1.0)  # TTS speech rate
    preferred_voice = db.Column(db.String(50), default='en-US-Standard-A')
    theme_preference = db.Column(db.String(20), default='auto')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
