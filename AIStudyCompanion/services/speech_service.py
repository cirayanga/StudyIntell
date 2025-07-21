import os
import logging
import tempfile
import base64
from typing import Optional, Dict, Any
import requests
from google.cloud import texttospeech
import assemblyai as aai

logger = logging.getLogger(__name__)

class SpeechService:
    def __init__(self):
        # Initialize AssemblyAI
        self.assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if self.assemblyai_api_key:
            aai.settings.api_key = self.assemblyai_api_key
        else:
            logger.warning("AssemblyAI API key not found")
        
        # Initialize Google TTS
        self.google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.tts_client = None
        if self.google_credentials:
            try:
                self.tts_client = texttospeech.TextToSpeechClient()
            except Exception as e:
                logger.warning(f"Google TTS client initialization failed: {e}")
                self.tts_client = None
        else:
            logger.info("Google TTS credentials not provided, using fallback TTS")
    
    def transcribe_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio using AssemblyAI"""
        if not self.assemblyai_api_key:
            return {
                "text": "",
                "success": False,
                "error": "AssemblyAI API key not configured"
            }
        
        try:
            # Save audio data to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Transcribe using AssemblyAI
            transcriber = aai.Transcriber()
            transcript = transcriber.transcribe(temp_file_path)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            if transcript.status == aai.TranscriptStatus.error:
                return {
                    "text": "",
                    "success": False,
                    "error": transcript.error
                }
            else:
                return {
                    "text": transcript.text,
                    "success": True,
                    "confidence": getattr(transcript, 'confidence', 0.8),
                    "duration": getattr(transcript, 'audio_duration', 0)
                }
                
        except Exception as e:
            logger.error(f"AssemblyAI transcription error: {e}")
            return {
                "text": "",
                "success": False,
                "error": str(e)
            }
    
    def text_to_speech(self, text: str, voice_name: str = "en-US-Standard-A", speed: float = 1.0) -> Dict[str, Any]:
        """Convert text to speech using Google TTS"""
        if not self.tts_client:
            return {
                "audio_data": None,
                "success": False,
                "error": "Google TTS client not initialized"
            }
        
        try:
            # Set up the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Set up the voice parameters
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name
            )
            
            # Set up the audio configuration
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed
            )
            
            # Perform the text-to-speech request
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Encode audio data as base64 for web transmission
            audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
            
            return {
                "audio_data": audio_base64,
                "success": True,
                "format": "mp3"
            }
            
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return {
                "audio_data": None,
                "success": False,
                "error": str(e)
            }
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available TTS voices"""
        if not self.tts_client:
            return {
                "voices": [],
                "success": False,
                "error": "Google TTS client not initialized"
            }
        
        try:
            # Get list of available voices
            voices = self.tts_client.list_voices()
            
            # Filter for English voices and format response
            english_voices = []
            for voice in voices.voices:
                if voice.language_codes[0].startswith('en'):
                    english_voices.append({
                        "name": voice.name,
                        "language": voice.language_codes[0],
                        "gender": voice.ssml_gender.name
                    })
            
            return {
                "voices": english_voices,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error getting available voices: {e}")
            return {
                "voices": [],
                "success": False,
                "error": str(e)
            }

# Alternative TTS implementation using Web Speech API fallback
class WebSpeechService:
    """Fallback service that uses client-side Web Speech API"""
    
    @staticmethod
    def get_fallback_tts_script():
        """Return JavaScript code for client-side TTS as fallback"""
        return """
        function speakText(text, voice='en-US', rate=1.0) {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = voice;
                utterance.rate = rate;
                utterance.pitch = 1;
                utterance.volume = 1;
                
                speechSynthesis.speak(utterance);
                return true;
            }
            return false;
        }
        
        function getAvailableVoices() {
            if ('speechSynthesis' in window) {
                return speechSynthesis.getVoices();
            }
            return [];
        }
        """
