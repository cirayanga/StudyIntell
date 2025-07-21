import os
import logging
from typing import Dict, Any, Optional
import cohere
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Initialize Cohere client
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        if self.cohere_api_key:
            self.cohere_client = cohere.Client(self.cohere_api_key)
        else:
            logger.warning("Cohere API key not found")
            self.cohere_client = None
            
        # Initialize Together AI client
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        if self.together_api_key:
            self.together_client = OpenAI(
                api_key=self.together_api_key,
                base_url="https://api.together.xyz/v1"
            )
        else:
            logger.warning("Together AI API key not found")
            self.together_client = None
    
    def generate_response_cohere(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Generate text response using Cohere API"""
        if not self.cohere_client:
            return None
            
        try:
            response = self.cohere_client.chat(
                message=prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                k=0,
                stop_sequences=["--"]
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Cohere API error: {e}")
            return None
    
    def generate_response_together(self, messages: list, model: str = "meta-llama/Llama-3-8b-chat-hf") -> Optional[str]:
        """Generate text response using Together AI API"""
        if not self.together_client:
            return None
            
        try:
            response = self.together_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                top_p=0.9,
                stop=["<|eot_id|>", "<|end_of_text|>"],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Together AI API error: {e}")
            return None
    
    def enhance_prompt_for_study(self, user_input: str, context: str = "") -> str:
        """Enhance user input for study-focused responses"""
        study_prompt = f"""
You are an AI Study Buddy designed to help students learn effectively. You provide clear, educational responses that encourage learning and understanding.

Context from previous conversations: {context}

Student's question or input: {user_input}

Please provide a helpful, educational response that:
1. Directly addresses the student's question
2. Explains concepts clearly and simply
3. Provides examples when helpful
4. Encourages further learning
5. Asks follow-up questions to deepen understanding

Response:"""
        return study_prompt
    
    def get_study_response(self, user_input: str, context: str = "", conversation_history: list = None) -> Dict[str, Any]:
        """Get a study-focused response using available AI services"""
        enhanced_prompt = self.enhance_prompt_for_study(user_input, context)
        
        # Try Together AI first (generally better for conversational AI)
        if self.together_client:
            messages = [
                {"role": "system", "content": "You are a helpful AI Study Buddy. Provide clear, educational responses that help students learn effectively."},
                {"role": "user", "content": enhanced_prompt}
            ]
            
            # Add conversation history if available
            if conversation_history:
                for conv in conversation_history[-5:]:  # Last 5 conversations for context
                    messages.insert(-1, {"role": "user", "content": conv.get('user_input', '')})
                    messages.insert(-1, {"role": "assistant", "content": conv.get('ai_response', '')})
            
            response = self.generate_response_together(messages)
            if response:
                return {
                    "response": response,
                    "source": "together_ai",
                    "success": True
                }
        
        # Fallback to Cohere
        if self.cohere_client:
            response = self.generate_response_cohere(enhanced_prompt)
            if response:
                return {
                    "response": response,
                    "source": "cohere",
                    "success": True
                }
        
        # Final fallback
        return {
            "response": "I'm having trouble connecting to my AI services right now. Please try again in a moment, or check that your API keys are properly configured.",
            "source": "fallback",
            "success": False
        }
    
    def summarize_session(self, conversations: list) -> str:
        """Generate a summary of the study session"""
        if not conversations:
            return "No conversations in this session yet."
        
        conversation_text = "\n".join([
            f"Student: {conv.get('user_input', '')}\nAI: {conv.get('ai_response', '')}"
            for conv in conversations[-10:]  # Last 10 conversations
        ])
        
        summary_prompt = f"""
Please provide a brief summary of this study session, highlighting key topics discussed and learning points:

{conversation_text}

Summary:"""
        
        # Try Together AI first
        if self.together_client:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes study sessions."},
                {"role": "user", "content": summary_prompt}
            ]
            response = self.generate_response_together(messages)
            if response:
                return response
        
        # Fallback to Cohere
        if self.cohere_client:
            response = self.generate_response_cohere(summary_prompt, max_tokens=200)
            if response:
                return response
        
        return "Study session summary unavailable at this time."
