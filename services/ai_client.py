import os
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
from openai import OpenAI

class AIClient:
    """Unified AI client supporting multiple providers with dynamic configuration"""
    
    def __init__(self):
        self._setup_client()
    
    def _setup_client(self):
        """Setup the appropriate AI client based on current configuration"""
        # Load configuration from ai_config.py
        try:
            from .ai_config import get_current_config
            config = get_current_config()
            self.provider = config.get("provider", "gemini").lower()
            self.current_model = config.get("model", "gemini-1.5-flash")
        except:
            # Fallback to environment variables
            self.provider = os.getenv("AI_PROVIDER", "gemini").lower()
            self.current_model = None
        
        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model_name = self.current_model or "gemini-1.5-flash"
                self.client = genai.GenerativeModel(model_name)
            else:
                self.client = None
        
        elif self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key
                )
                self.model = self.current_model or os.getenv("OPENROUTER_MODEL", "gpt-4")
            else:
                self.client = None
        
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def reload_config(self):
        """Reload configuration and reinitialize client"""
        self._setup_client()
    
    async def generate_content(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate content using the configured AI provider"""
        if not self.client:
            raise Exception(f"No API key configured for {self.provider}")
        
        if self.provider == "gemini":
            return await self._generate_gemini(prompt, system_prompt)
        elif self.provider == "openrouter":
            return await self._generate_openrouter(prompt, system_prompt)
        else:
            raise Exception(f"Provider {self.provider} not implemented")
    
    async def _generate_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate content using Gemini"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.client.generate_content(full_prompt)
        return response.text.strip()
    
    async def _generate_openrouter(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate content using OpenRouter"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        info = {
            "provider": self.provider,
            "configured": self.client is not None,
            "model": self.current_model
        }
        
        return info

# Global AI client instance
ai_client = AIClient()