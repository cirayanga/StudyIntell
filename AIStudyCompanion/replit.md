# AI Study Buddy

## Overview

AI Study Buddy is a Flask-based web application that provides an interactive AI-powered learning experience with voice and text input capabilities. The application combines multiple AI services to create an intelligent tutoring system that can understand spoken questions, provide detailed responses, and maintain conversation history across study sessions.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### July 13, 2025 - Voice Recording Issues Fixed
- Fixed voice input processing state management preventing AI responses
- Improved JavaScript error handling for TTS synthesis
- Created missing preferences.html template with voice settings
- Enhanced text escaping for JavaScript to prevent syntax errors
- Voice recording now fully functional with transcription and AI responses

## System Architecture

The application follows a traditional web architecture pattern with clear separation of concerns:

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy for database operations
- **Database**: SQLite for local development (configurable to PostgreSQL via DATABASE_URL)
- **API Design**: RESTful API endpoints with separate blueprints for main routes and API routes
- **Services Layer**: Modular service classes for AI, speech processing, and RAG (Retrieval-Augmented Generation)

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **JavaScript**: Vanilla JavaScript for real-time audio recording and chat interactions
- **Styling**: Custom CSS with CSS variables for theming and Bootstrap components

### Data Storage
- **Primary Database**: SQLAlchemy ORM with support for both SQLite and PostgreSQL
- **Vector Storage**: FAISS vector store for knowledge base embeddings
- **Session Management**: Flask sessions for user state management

## Key Components

### Database Models
1. **StudySession**: Manages individual study sessions with conversation tracking
2. **Conversation**: Stores user inputs and AI responses with metadata
3. **KnowledgeBase**: Stores reference materials with vector embeddings for RAG
4. **UserPreferences**: Manages user settings and preferences

### Service Layer
1. **AIService**: Integrates multiple AI providers (Cohere, Together AI, OpenAI)
2. **SpeechService**: Handles speech-to-text (AssemblyAI) and text-to-speech (Google TTS)
3. **RAGService**: Implements retrieval-augmented generation using LangChain and vector embeddings

### Middleware
1. **RateLimiter**: Implements service-specific rate limiting with circuit breaker pattern
2. **ProxyFix**: Handles proxy headers for deployment scenarios

## Data Flow

### Voice Interaction Flow
1. User clicks voice button → JavaScript captures audio via Web Audio API
2. Audio data sent to `/api/transcribe` → AssemblyAI converts speech to text
3. Transcribed text processed by AI service → Cohere/Together AI generates response
4. Response stored in database → Google TTS converts to audio
5. Audio played back to user → Conversation saved to study session

### Text Interaction Flow
1. User submits text input → Direct processing by AI service
2. AI generates contextual response → RAG service enhances with knowledge base
3. Response stored and displayed → Optional TTS conversion for audio output

### Knowledge Base Integration
1. Documents processed through LangChain text splitters
2. Embeddings generated via Cohere → Stored in FAISS vector store
3. Query matching during conversation → Relevant context injected into AI prompts

## External Dependencies

### AI Services
- **Cohere**: Primary language model for response generation and embeddings
- **Together AI**: Alternative language model provider with OpenAI-compatible API
- **AssemblyAI**: Speech-to-text transcription service
- **Google Text-to-Speech**: High-quality voice synthesis

### Infrastructure
- **LangChain**: Framework for RAG implementation and document processing
- **FAISS**: Vector similarity search for knowledge retrieval
- **Bootstrap 5**: Frontend UI framework
- **Font Awesome**: Icon library

### Environment Variables Required
- `COHERE_API_KEY`: For language model and embeddings
- `TOGETHER_API_KEY`: Alternative AI provider
- `ASSEMBLYAI_API_KEY`: Speech recognition
- `GOOGLE_APPLICATION_CREDENTIALS`: TTS service authentication
- `DATABASE_URL`: Database connection string
- `SESSION_SECRET`: Flask session security

## Deployment Strategy

### Development Environment
- SQLite database for local development
- Debug mode enabled with hot reloading
- Logging configured for development debugging

### Production Considerations
- PostgreSQL database support via environment variables
- Rate limiting and circuit breakers for API stability
- Proxy middleware for reverse proxy deployment
- Session security with configurable secret keys

### Scalability Features
- Connection pooling with automatic reconnection
- Service-specific rate limiting to prevent API quota exhaustion
- Modular service architecture for easy horizontal scaling
- Vector store caching for improved RAG performance

The application is designed to be easily deployable on platforms like Replit, Heroku, or similar cloud services with minimal configuration changes.