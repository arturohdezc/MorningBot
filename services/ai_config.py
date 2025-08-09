import json
import os
from typing import Dict, List, Any

AI_CONFIG_FILE = "ai_config.json"

# Available models for each provider
AVAILABLE_MODELS = {
    "gemini": [
        {
            "id": "gemini-1.5-flash",
            "name": "Gemini 1.5 Flash",
            "description": "Rápido y eficiente",
        },
        {
            "id": "gemini-2.0-flash-exp",
            "name": "Gemini 2.0 Flash",
            "description": "Versión 2.0 rápida",
        },
        {
            "id": "gemini-2.0-flash-thinking-exp",
            "name": "Gemini 2.0 Flash Exp",
            "description": "Versión 2.0 experimental",
        },
    ],
    "openrouter": [
        # FREE MODELS - Updated list
        {
            "id": "openai/gpt-oss-20b:free",
            "name": "GPT OSS 20B (Free)",
            "description": "OpenAI GPT OSS 20B - Gratis",
        },
        {
            "id": "zhipuai/glm-4.5-air:free",
            "name": "GLM 4.5 Air (Free)",
            "description": "Z.AI GLM 4.5 Air - Gratis",
        },
        {
            "id": "qwen/qwen-3-coder:free",
            "name": "Qwen3 Coder (Free)",
            "description": "Qwen Qwen3 Coder - Gratis",
        },
        {
            "id": "moonshot/kimi-k2:free",
            "name": "Kimi K2 (Free)",
            "description": "MoonshotAI Kimi K2 - Gratis",
        },
        {
            "id": "deepseek/r1-0528:free",
            "name": "DeepSeek R1 0528 (Free)",
            "description": "DeepSeek R1 0528 - Gratis",
        },
        {
            "id": "google/gemma-3n-2b:free",
            "name": "Gemma 3n 2B (Free)",
            "description": "Google Gemma 3n 2B - Gratis",
        },
        {
            "id": "huggingfaceh4/zephyr-7b-beta:free",
            "name": "Zephyr 7B Beta (Free)",
            "description": "HuggingFace Zephyr 7B - Gratis",
        },
        {
            "id": "openchat/openchat-7b:free",
            "name": "OpenChat 7B (Free)",
            "description": "OpenChat 7B - Gratis",
        },
        {
            "id": "gryphe/mythomist-7b:free",
            "name": "Mythomist 7B (Free)",
            "description": "Gryphe Mythomist 7B - Gratis",
        },
    ],
}


def load_ai_config() -> Dict[str, Any]:
    """Load AI configuration from file"""
    try:
        if os.path.exists(AI_CONFIG_FILE):
            with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return get_default_ai_config()
    except Exception as e:
        print(f"Error loading AI config: {e}")
        return get_default_ai_config()


def save_ai_config(config: Dict[str, Any]) -> bool:
    """Save AI configuration to file"""
    try:
        with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
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
        "last_updated": None,
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
            gemini_configured
            if current_provider == "gemini"
            else openrouter_configured
            if current_provider == "openrouter"
            else False
        ),
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

    if not config["provider_configured"]:
        message += f"\n⚠️ Configura la API key para {config['provider']} o el sistema usará fallback heurístico"

    return message
