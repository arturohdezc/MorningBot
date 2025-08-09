#!/usr/bin/env python3
"""
Script para codificar archivos de Google en base64
Para usar en variables de entorno de Render
"""

import base64
import json
import os
from datetime import datetime


def encode_file_to_base64(filename):
    """Codifica un archivo a base64"""
    if not os.path.exists(filename):
        print(f"❌ Archivo {filename} no encontrado")
        return None

    with open(filename, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")

    print(f"✅ {filename} codificado correctamente")
    return encoded


def encode_multi_account_tokens():
    """Codifica tokens de multi-cuenta si existen"""
    tokens_file = "multi_account_tokens.json"
    
    if not os.path.exists(tokens_file):
        print(f"❌ {tokens_file} no encontrado")
        print("ℹ️  Ejecuta 'python oauth_server.py' primero para generar tokens")
        return None
    
    try:
        with open(tokens_file, 'r') as f:
            tokens_data = json.load(f)
        
        # Verificar que hay tokens válidos
        if not tokens_data:
            print(f"❌ {tokens_file} está vacío")
            return None
        
        # Codificar a base64
        tokens_json = json.dumps(tokens_data)
        encoded = base64.b64encode(tokens_json.encode()).decode('utf-8')
        
        print(f"✅ {tokens_file} codificado correctamente")
        print(f"📧 Cuentas encontradas: {len(tokens_data)}")
        for account in tokens_data.keys():
            print(f"   - {account}")
        
        return encoded
        
    except Exception as e:
        print(f"❌ Error procesando {tokens_file}: {e}")
        return None


if __name__ == "__main__":
    print("🔧 Codificando archivos de Google para Render...")
    print(f"⏰ Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Codificar credentials.json (estático)
    credentials_encoded = encode_file_to_base64("credentials.json")
    
    # Codificar multi_account_tokens.json (dinámico)
    tokens_encoded = encode_multi_account_tokens()
    
    print("\n" + "="*60)
    print("📤 VARIABLES PARA RENDER:")
    print("="*60)
    
    if credentials_encoded:
        print(f"CREDENTIALS_JSON_BASE64={credentials_encoded}")
        print()
    
    if tokens_encoded:
        print(f"MULTI_ACCOUNT_TOKENS_BASE64={tokens_encoded}")
        print()
        print("✅ ¡Tokens multi-cuenta listos!")
    else:
        print("⚠️  MULTI_ACCOUNT_TOKENS_BASE64 no disponible")
        print("📋 Para generar tokens:")
        print("   1. Ejecuta: python oauth_server.py")
        print("   2. Configura tus cuentas Gmail")
        print("   3. Ejecuta este script de nuevo")
        print()
    
    if not credentials_encoded:
        print("❌ CREDENTIALS_JSON_BASE64 no disponible")
        print("📋 Para obtener credentials.json:")
        print("   1. Ir a https://console.cloud.google.com/")
        print("   2. Crear proyecto y habilitar APIs (Gmail, Calendar, Tasks)")
        print("   3. Crear credenciales OAuth 2.0 (Aplicación web)")
        print("   4. Descargar JSON y renombrar a 'credentials.json'")
        print("   5. Ejecutar este script de nuevo")
    
    print("="*60)
