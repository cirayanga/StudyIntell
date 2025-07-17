from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app import db
from models import StudySession, Conversation, UserPreferences
import uuid
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Main landing page"""
    # Initialize session if needed
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Get or create user preferences
    prefs = UserPreferences.query.filter_by(session_id=session['session_id']).first()
    if not prefs:
        prefs = UserPreferences(session_id=session['session_id'])
        db.session.add(prefs)
        db.session.commit()
    
    # Get recent study sessions
    recent_sessions = StudySession.query.order_by(StudySession.updated_at.desc()).limit(5).all()
    
    return render_template('index.html', 
                         recent_sessions=recent_sessions,
                         user_preferences=prefs)

@main_bp.route('/study/<int:session_id>')
def study_session(session_id):
    """Study session page"""
    study_session = StudySession.query.get_or_404(session_id)
    
    # Get conversation history
    conversations = Conversation.query.filter_by(session_id=session_id)\
                                    .order_by(Conversation.timestamp.asc()).all()
    
    # Get user preferences
    prefs = UserPreferences.query.filter_by(session_id=session.get('session_id', '')).first()
    
    return render_template('study_session.html',
                         study_session=study_session,
                         conversations=conversations,
                         user_preferences=prefs)

@main_bp.route('/new_session', methods=['POST'])
def new_session():
    """Create a new study session"""
    session_name = request.form.get('session_name', 'New Study Session')
    
    try:
        new_study_session = StudySession(session_name=session_name)
        db.session.add(new_study_session)
        db.session.commit()
        
        flash(f'Created new study session: {session_name}', 'success')
        return redirect(url_for('main.study_session', session_id=new_study_session.id))
        
    except Exception as e:
        logger.error(f"Error creating study session: {e}")
        flash('Error creating study session. Please try again.', 'error')
        return redirect(url_for('main.index'))

@main_bp.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    """Delete a study session"""
    try:
        study_session = StudySession.query.get_or_404(session_id)
        db.session.delete(study_session)
        db.session.commit()
        
        flash('Study session deleted successfully.', 'success')
        
    except Exception as e:
        logger.error(f"Error deleting study session: {e}")
        flash('Error deleting study session.', 'error')
    
    return redirect(url_for('main.index'))

@main_bp.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """User preferences page"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    prefs = UserPreferences.query.filter_by(session_id=session['session_id']).first()
    if not prefs:
        prefs = UserPreferences(session_id=session['session_id'])
        db.session.add(prefs)
        db.session.commit()
    
    if request.method == 'POST':
        try:
            prefs.voice_enabled = request.form.get('voice_enabled') == 'on'
            prefs.speech_rate = float(request.form.get('speech_rate', 1.0))
            prefs.preferred_voice = request.form.get('preferred_voice', 'en-US-Standard-A')
            prefs.theme_preference = request.form.get('theme_preference', 'auto')
            
            db.session.commit()
            flash('Preferences updated successfully!', 'success')
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            flash('Error updating preferences.', 'error')
            db.session.rollback()
    
    return render_template('preferences.html', preferences=prefs)

@main_bp.before_request
def before_request():
    """Setup session and logging for each request"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    logger.debug(f"Request: {request.method} {request.path} from {request.remote_addr}")

@main_bp.after_request
def after_request(response):
    """Add security headers and CORS if needed"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response
