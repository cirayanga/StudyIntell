/**
 * Study Buddy JavaScript
 * Handles chat interactions, voice controls, and UI updates
 */

class StudyBuddy {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.isRecording = false;
        this.isProcessing = false;
        this.lastAiResponse = '';
        this.initializeEventListeners();
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        // Voice button
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn) {
            voiceBtn.addEventListener('click', () => this.toggleRecording());
        }

        // Chat form
        const chatForm = document.getElementById('chatForm');
        if (chatForm) {
            chatForm.addEventListener('submit', (e) => this.handleTextSubmit(e));
        }

        // Play last response button
        const playBtn = document.getElementById('playLastResponseBtn');
        if (playBtn) {
            playBtn.addEventListener('click', () => this.playLastResponse());
        }

        // Message input
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleTextSubmit(e);
                }
            });
        }
    }

    /**
     * Toggle voice recording
     */
    async toggleRecording() {
        if (this.isRecording) {
            await this.stopVoiceInput();
        } else {
            await this.startVoiceInput();
        }
    }

    /**
     * Start voice input recording
     */
    async startVoiceInput() {
        if (this.isProcessing) return;

        try {
            await startRecording();
            this.isRecording = true;
            this.updateVoiceButton(true);
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showError('Failed to start recording. Please check your microphone permissions.');
        }
    }

    /**
     * Stop voice input and process
     */
    async stopVoiceInput() {
        if (!this.isRecording || this.isProcessing) return;

        try {
            this.isProcessing = true;
            this.updateVoiceButton(false, true);

            // Stop recording and get audio blob
            const audioBlob = await stopRecording();
            this.isRecording = false;

            // Show transcription indicator
            this.updateVoiceButton(false, true);
            
            // Transcribe audio
            const transcription = await transcribeAudio(audioBlob);
            console.log('Transcription result:', transcription);

            if (transcription.success && transcription.text && transcription.text.trim()) {
                console.log('Sending transcribed message:', transcription.text);
                // First add the transcribed text to the chat as user message
                this.addMessageToChat(transcription.text, 'user', 'voice');
                
                // Reset processing state before sending to AI
                this.isProcessing = false;
                
                // Then send to AI
                await this.sendMessage(transcription.text, 'voice', transcription.duration || 0);
            } else {
                const errorMsg = transcription.error || 'Could not understand the audio. Please try again.';
                console.error('Transcription failed:', errorMsg);
                this.showError(errorMsg);
            }
        } catch (error) {
            console.error('Voice input error:', error);
            this.showError('Voice input failed: ' + error.message);
        } finally {
            this.isRecording = false;
            this.isProcessing = false;
            this.updateVoiceButton(false, false);
        }
    }

    /**
     * Handle text form submission
     */
    async handleTextSubmit(event) {
        event.preventDefault();
        
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message || this.isProcessing) return;
        
        messageInput.value = '';
        await this.sendMessage(message, 'text');
    }

    /**
     * Send message to AI and update UI
     */
    async sendMessage(message, inputMethod = 'text', audioDuration = 0) {
        if (this.isProcessing) return;

        try {
            this.isProcessing = true;
            
            // Add user message to chat (only if not voice, as voice already added)
            if (inputMethod !== 'voice') {
                this.addMessageToChat(message, 'user', inputMethod);
            }
            
            // Show typing indicator
            const typingId = this.showTypingIndicator();
            
            // Send to API
            console.log('Sending to API:', { message, inputMethod, sessionId: this.sessionId });
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId,
                    input_method: inputMethod,
                    audio_duration: audioDuration
                })
            });

            const result = await response.json();
            console.log('API response:', result);
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);

            if (result.success) {
                // Add AI response to chat
                this.addMessageToChat(result.response, 'ai');
                this.lastAiResponse = result.response;
                
                // Update recommendations
                this.updateRecommendations(result.recommendations || []);
                
                // Enable play button
                const playBtn = document.getElementById('playLastResponseBtn');
                if (playBtn) {
                    playBtn.disabled = false;
                }
                
                // Auto-play response if voice input was used
                if (inputMethod === 'voice') {
                    setTimeout(() => this.speakText(result.response), 500);
                }
            } else {
                this.addMessageToChat(
                    result.fallback_response || 'Sorry, I encountered an error. Please try again.',
                    'ai',
                    'error'
                );
                
                if (result.error) {
                    this.showError(result.error);
                }
            }
        } catch (error) {
            console.error('Send message error:', error);
            this.showError('Failed to send message. Please check your connection and try again.');
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Add message to chat UI
     */
    addMessageToChat(message, sender, inputMethod = '', status = '') {
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        let metaIcon = 'fas fa-robot';
        let metaText = 'AI Response';
        
        if (sender === 'user') {
            metaIcon = inputMethod === 'voice' ? 'fas fa-microphone' : 'fas fa-keyboard';
            metaText = timeString;
        }
        
        if (status === 'error') {
            messageDiv.classList.add('error');
        }

        messageDiv.innerHTML = `
            <div class="message-bubble">
                ${this.escapeHtml(message)}
            </div>
            <div class="message-meta">
                <i class="${metaIcon} me-1"></i>${metaText}
                ${sender === 'ai' ? `
                    <button class="btn btn-sm btn-link p-0 ms-2" onclick="studyBuddy.speakText('${this.escapeForJs(message)}')">
                        <i class="fas fa-volume-up"></i>
                    </button>
                ` : ''}
            </div>
        `;

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return null;

        const typingDiv = document.createElement('div');
        typingDiv.className = 'message ai typing-indicator';
        typingDiv.id = 'typing-' + Date.now();
        
        typingDiv.innerHTML = `
            <div class="message-bubble">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
            <div class="message-meta">
                <i class="fas fa-robot me-1"></i>Thinking...
            </div>
        `;

        chatContainer.appendChild(typingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return typingDiv.id;
    }

    /**
     * Remove typing indicator
     */
    removeTypingIndicator(typingId) {
        if (typingId) {
            const typingDiv = document.getElementById(typingId);
            if (typingDiv) {
                typingDiv.remove();
            }
        }
    }

    /**
     * Update voice button appearance
     */
    updateVoiceButton(isRecording, isProcessing = false) {
        const voiceBtn = document.getElementById('voiceBtn');
        const indicator = document.getElementById('recordingIndicator');
        
        if (!voiceBtn) return;

        if (isProcessing) {
            voiceBtn.innerHTML = '<div class="spinner-border spinner-border-sm me-2"></div>Processing...';
            voiceBtn.disabled = true;
            voiceBtn.className = 'btn btn-secondary btn-lg me-2';
        } else if (isRecording) {
            voiceBtn.innerHTML = '<i class="fas fa-stop me-2"></i>Stop Recording';
            voiceBtn.className = 'btn btn-danger btn-lg me-2';
            if (indicator) indicator.style.display = 'block';
        } else {
            voiceBtn.innerHTML = '<i class="fas fa-microphone me-2"></i>Start Recording';
            voiceBtn.className = 'btn btn-light btn-lg me-2';
            voiceBtn.disabled = false;
            if (indicator) indicator.style.display = 'none';
        }
    }

    /**
     * Speak text using TTS
     */
    async speakText(text) {
        if (!text || !text.trim()) return;
        
        try {
            // Try API-based TTS first
            const result = await synthesizeSpeech(text);
            
            if (result && result.success && result.audio_data) {
                playAudioFromBase64(result.audio_data, result.format);
            } else {
                // Fallback to Web Speech API
                this.fallbackToWebSpeech(text);
            }
        } catch (error) {
            console.error('TTS error:', error);
            // Fallback to Web Speech API
            this.fallbackToWebSpeech(text);
        }
    }

    /**
     * Fallback to Web Speech API for TTS
     */
    fallbackToWebSpeech(text) {
        try {
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                utterance.volume = 1.0;
                
                // Get available voices and use a good one if available
                const voices = speechSynthesis.getVoices();
                const englishVoice = voices.find(voice => 
                    voice.lang.startsWith('en') && voice.localService
                );
                if (englishVoice) {
                    utterance.voice = englishVoice;
                }
                
                speechSynthesis.speak(utterance);
            } else {
                console.warn('Speech synthesis not supported');
            }
        } catch (error) {
            console.error('Web Speech fallback error:', error);
        }
    }

    /**
     * Play last AI response
     */
    playLastResponse() {
        if (this.lastAiResponse) {
            this.speakText(this.lastAiResponse);
        }
    }

    /**
     * Update study recommendations
     */
    updateRecommendations(recommendations) {
        const recommendationsDiv = document.getElementById('recommendations');
        if (!recommendationsDiv) return;

        if (recommendations.length === 0) {
            recommendationsDiv.innerHTML = '<p class="text-muted">No specific recommendations at this time.</p>';
            return;
        }

        const listHtml = recommendations.map(rec => `
            <div class="d-flex align-items-start mb-2">
                <i class="fas fa-lightbulb text-warning me-2 mt-1"></i>
                <span class="small">${this.escapeHtml(rec)}</span>
            </div>
        `).join('');

        recommendationsDiv.innerHTML = listHtml;
    }

    /**
     * Show error message
     */
    showError(message) {
        // Create toast notification
        const toastContainer = this.getOrCreateToastContainer();
        
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-triangle me-2"></i>${this.escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 5000 });
        bsToast.show();

        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    /**
     * Get or create toast container
     */
    getOrCreateToastContainer() {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '1050';
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape text for JavaScript string
     */
    escapeForJs(text) {
        return text
            .replace(/\\/g, '\\\\')  // Escape backslashes first
            .replace(/'/g, "\\'")     // Escape single quotes
            .replace(/"/g, '\\"')     // Escape double quotes
            .replace(/\n/g, '\\n')    // Escape newlines
            .replace(/\r/g, '\\r')    // Escape carriage returns
            .replace(/\t/g, '\\t')    // Escape tabs
            .replace(/\u2028/g, '\\u2028')  // Escape line separator
            .replace(/\u2029/g, '\\u2029'); // Escape paragraph separator
    }
}

// Global study buddy instance
let studyBuddy = null;

/**
 * Initialize study buddy
 */
function initializeStudyBuddy(sessionId) {
    studyBuddy = new StudyBuddy(sessionId);
    console.log('Study buddy initialized for session:', sessionId);
}

// CSS for typing indicator
const typingStyles = `
    .typing-dots {
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    .typing-dots span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #6c757d;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { 
            transform: scale(0);
            opacity: 0.5;
        }
        40% { 
            transform: scale(1);
            opacity: 1;
        }
    }
    
    .message.error .message-bubble {
        background-color: #f8d7da !important;
        border-color: #f5c6cb !important;
        color: #721c24 !important;
    }
`;

// Add typing styles to document
if (!document.getElementById('study-buddy-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'study-buddy-styles';
    styleSheet.textContent = typingStyles;
    document.head.appendChild(styleSheet);
}
