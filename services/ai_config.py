import json
import os
from typing import Dict, List, Any

AI_CONFIG_FILE = "ai_config.json"

# Available models for each provider
AVAILABLE_MODELS = {
    "gemini": [
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "description": "Rápido y eficiente"},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "description": "Más potente y preciso"}
    ],
    "openrouter": [
        {"id": "gpt-4", "name": "GPT-4", "description": "OpenAI GPT-4"},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "OpenAI GPT-3.5 Turbo"},
        {"id": "claude-3-opus", "name": "Claude 3 Opus", "description": "Anthropic Claude 3 Opus"},
        {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "description": "Anthropic Claude 3 Sonnet"},
        {"id": "claude-3-haiku", "name": "Claude 3 Haiku", "description": "Anthropic Claude 3 Haiku"},
        {"id": "llama-3-70b", "name": "Llama 3 70B", "description": "Meta Llama 3 70B"},
        {"id": "mixtral-8x7b", "name": "Mixtral 8x7B", "description": "Mistral Mixtral 8x7B"}
    ]
}

def load_ai_config() -> Dict[str, Any]:
    """Load AI configuration from file"""
    try:
        if os.path.exists(AI_CONFIG_FILE):
            with open(AI_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return get_default_ai_config()
    except Exception as e:
        print(f"Error loading AI config: {e}")
        return get_default_ai_config()

def save_ai_config(config: Dict[str, Any]) -> bool:
    """Save AI configuration to file"""
    try:
        with open(AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving AI config: {e}")
        return False

def get_default_ai_config() -> Dict[str, Any]:
    """Get default AI configuration"""
    return {
        "provider": os.getenv("AI_PROVIDER", "gemini"),
        "gemini_model": "gemini-1.5-flash",
        "openrouter_model": os.getenv("OPENROUTER_MODEL", "gpt-4"),
        "last_updated": None
    }

def update_ai_provider(provider: str, model: str = None) -> Dict[str, Any]:
    """Update AI provider and model"""
    config = load_ai_config()
    config["provider"] = provider
    
    if provider == "gemini":
        config["gemini_model"] = model or "gemini-1.5-flash"
    elif provider == "openrouter":
        config["openrouter_model"] = model or "gpt-4"
    
    config["last_updated"] = json.dumps({"timestamp": "now"})  # Simple timestamp
    
    if save_ai_config(config):
        # Update environment variable for immediate effect
        os.environ["AI_PROVIDER"] = provider
        if provider == "openrouter" and model:
            os.environ["OPENROUTER_MODEL"] = model
        
        return config
    else:
        raise Exception("Failed to save AI configuration")

def get_available_models(provider: str) -> List[Dict[str, str]]:
    """Get available models for a provider"""
    return AVAILABLE_MODELS.get(provider, [])

def get_current_config() -> Dict[str, Any]:
    """Get current AI configuration with status"""
    config = load_ai_config()
    
    # Check if API keys are configured
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    openrouter_configured = bool(os.getenv("OPENROUTER_API_KEY"))
    
    current_provider = config.get("provider", "gemini")
    current_model = None
    
    if current_provider == "gemini":
        current_model = config.get("gemini_model", "gemini-1.5-flash")
    elif current_provider == "openrouter":
        current_model = config.get("openrouter_model", "gpt-4")
    
    return {
        "provider": current_provider,
        "model": current_model,
        "gemini_configured": gemini_configured,
        "openrouter_configured": openrouter_configured,
        "provider_configured": (
            gemini_configured if current_provider == "gemini" 
            else openrouter_configured if current_provider == "openrouter" 
            else False
        )
    }

def format_ai_config_message() -> str:
    """Format AI configuration for display"""
    config = get_current_config()
    
    message = "🤖 *Configuración de IA*\n\n"
    message += f"**Proveedor actual:** {config['provider'].title()}\n"
    message += f"**Modelo actual:** {config['model']}\n"
    message += f"**Estado:** {'✅ Configurado' if config['provider_configured'] else '❌ Sin API Key'}\n\n"
    
    message += "**Proveedores disponibles:**\n"
    message += f"• Gemini: {'✅' if config['gemini_configured'] else '❌'}\n"
    message += f"• OpenRouter: {'✅' if config['openrouter_configured'] else '❌'}\n"
    
    if not config['provider_configured']:
        message += f"\n⚠️ Configura la API key para {config['provider']} o el sistema usará fallback heurístico"
    
    return message