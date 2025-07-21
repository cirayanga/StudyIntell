/**
 * Audio Recorder for AI Study Buddy
 * Handles microphone recording and audio processing
 */

class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    /**
     * Initialize audio recording capabilities
     */
    async initialize() {
        try {
            // Check for browser support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Audio recording not supported in this browser');
            }

            // Get user media permissions
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            console.log('Audio recorder initialized successfully');
            return true;
        } catch (error) {
            console.error('Error initializing audio recorder:', error);
            throw error;
        }
    }

    /**
     * Start recording audio
     */
    async startRecording() {
        try {
            if (!this.stream) {
                await this.initialize();
            }

            this.audioChunks = [];
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            
            console.log('Recording started');
            return true;
        } catch (error) {
            console.error('Error starting recording:', error);
            throw error;
        }
    }

    /**
     * Stop recording and return audio blob
     */
    async stopRecording() {
        return new Promise((resolve, reject) => {
            if (!this.mediaRecorder || !this.isRecording) {
                reject(new Error('No active recording to stop'));
                return;
            }

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                this.isRecording = false;
                console.log('Recording stopped, blob size:', audioBlob.size);
                resolve(audioBlob);
            };

            this.mediaRecorder.onerror = (event) => {
                reject(new Error('Recording error: ' + event.error));
            };

            this.mediaRecorder.stop();
        });
    }

    /**
     * Check if currently recording
     */
    getRecordingState() {
        return this.isRecording;
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
    }
}

// Global audio recorder instance
let audioRecorder = new AudioRecorder();

/**
 * Start recording audio
 */
async function startRecording() {
    try {
        await audioRecorder.startRecording();
        
        // Update UI
        const recordBtn = document.getElementById('voiceBtn');
        if (recordBtn) {
            recordBtn.innerHTML = '<i class="fas fa-stop me-2"></i>Stop Recording';
            recordBtn.className = 'btn btn-danger btn-lg me-2';
        }
        
        // Show recording indicator
        const indicator = document.getElementById('recordingIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
        
        return true;
    } catch (error) {
        console.error('Failed to start recording:', error);
        
        // Show user-friendly error message
        if (error.message.includes('Permission denied')) {
            alert('Microphone permission is required. Please allow microphone access and try again.');
        } else if (error.message.includes('not supported')) {
            alert('Audio recording is not supported in your browser. Please use a modern browser like Chrome, Firefox, or Safari.');
        } else {
            alert('Failed to start recording: ' + error.message);
        }
        
        throw error;
    }
}

/**
 * Stop recording and return audio blob
 */
async function stopRecording() {
    try {
        const audioBlob = await audioRecorder.stopRecording();
        
        // Update UI
        const recordBtn = document.getElementById('voiceBtn');
        if (recordBtn) {
            recordBtn.innerHTML = '<i class="fas fa-microphone me-2"></i>Start Recording';
            recordBtn.className = 'btn btn-light btn-lg me-2';
        }
        
        // Hide recording indicator
        const indicator = document.getElementById('recordingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
        
        return audioBlob;
    } catch (error) {
        console.error('Failed to stop recording:', error);
        alert('Failed to stop recording: ' + error.message);
        throw error;
    }
}

/**
 * Transcribe audio using API
 */
async function transcribeAudio(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Transcription failed');
        }
        
        return result;
    } catch (error) {
        console.error('Transcription error:', error);
        throw error;
    }
}

/**
 * Convert text to speech using API
 */
async function synthesizeSpeech(text, voice = 'en-US-Standard-A', speed = 1.0) {
    try {
        const response = await fetch('/api/synthesize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                voice: voice,
                speed: speed
            })
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Speech synthesis failed');
        }
        
        return result;
    } catch (error) {
        console.error('Speech synthesis error:', error);
        throw error;
    }
}

/**
 * Play audio from base64 data
 */
function playAudioFromBase64(base64Data, format = 'mp3') {
    try {
        const audioData = `data:audio/${format};base64,${base64Data}`;
        const audio = new Audio(audioData);
        
        audio.play().catch(error => {
            console.error('Audio playback error:', error);
            // Fallback to Web Speech API
            fallbackToWebSpeech();
        });
        
        return audio;
    } catch (error) {
        console.error('Error creating audio element:', error);
        throw error;
    }
}

/**
 * Fallback to Web Speech API for TTS
 */
function fallbackToWebSpeech(text, voice = 'en-US', rate = 1.0) {
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

/**
 * Get available speech synthesis voices
 */
function getAvailableVoices() {
    if ('speechSynthesis' in window) {
        return speechSynthesis.getVoices();
    }
    return [];
}

/**
 * Check if audio recording is supported
 */
function isAudioRecordingSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

/**
 * Check if speech synthesis is supported
 */
function isSpeechSynthesisSupported() {
    return 'speechSynthesis' in window;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check for audio support and show warnings if needed
    if (!isAudioRecordingSupported()) {
        console.warn('Audio recording not supported');
        
        // Disable voice controls if present
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn) {
            voiceBtn.disabled = true;
            voiceBtn.innerHTML = '<i class="fas fa-microphone-slash me-2"></i>Not Supported';
            voiceBtn.title = 'Audio recording not supported in this browser';
        }
    }
    
    if (!isSpeechSynthesisSupported()) {
        console.warn('Speech synthesis not supported');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (audioRecorder) {
        audioRecorder.cleanup();
    }
});
