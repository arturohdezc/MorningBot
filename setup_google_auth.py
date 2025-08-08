#!/usr/bin/env python3
"""
Script para generar token.json para Google APIs
Ejecutar localmente antes de subir a Render
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes necesarios para el bot
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly', 
    'https://www.googleapis.com/auth/tasks'
]

def setup_google_credentials():
    """Configura las credenciales de Google OAuth"""
    creds = None
    
    # Verificar si ya existe token.json
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas, obtener nuevas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: credentials.json no encontrado")
                print("📋 Descarga credentials.json desde Google Cloud Console")
                return False
                
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardar credenciales para próximas ejecuciones
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("✅ Google OAuth configurado correctamente")
    print("📁 Archivos generados: token.json")
    return True

if __name__ == '__main__':
    print("🔧 Configurando Google OAuth...")
    success = setup_google_credentials()
    
    if success:
        print("\n✅ ¡Configuración completada!")
        print("📤 Ahora puedes subir el proyecto a GitHub")
    else:
        print("\n❌ Error en la configuración")
        print("🔍 Verifica que credentials.json esté en el directorio")