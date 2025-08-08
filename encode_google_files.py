#!/usr/bin/env python3
"""
Script para codificar archivos de Google en base64
Para usar en variables de entorno de Render
"""

import base64
import json
import os


def encode_file_to_base64(filename):
    """Codifica un archivo a base64"""
    if not os.path.exists(filename):
        print(f"❌ Archivo {filename} no encontrado")
        return None

    with open(filename, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("utf-8")

    print(f"✅ {filename} codificado correctamente")
    print(f"📋 Variable de entorno para Render:")
    print(f"{filename.upper().replace('.', '_')}_BASE64={encoded}")
    print("-" * 50)
    return encoded


if __name__ == "__main__":
    print("🔧 Codificando archivos de Google para Render...")
    print()

    # Solo necesitamos credentials.json para multi-cuenta OAuth
    credentials_encoded = encode_file_to_base64("credentials.json")

    if credentials_encoded:
        print("\n✅ ¡Listo para Render!")
        print("📤 Copia esta variable a Render Environment:")
        print(f"CREDENTIALS_JSON_BASE64={credentials_encoded}")
        print()
        print("ℹ️  NOTA: No necesitas token.json con la implementación multi-cuenta")
        print("ℹ️  El OAuth se hace directamente en Render para cada cuenta")
    else:
        print(
            "\n❌ Error: Necesitas descargar credentials.json de Google Cloud Console"
        )
        print("📋 Pasos:")
        print("1. Ir a https://console.cloud.google.com/")
        print("2. Crear proyecto y habilitar APIs (Gmail, Calendar, Tasks)")
        print("3. Crear credenciales OAuth 2.0 (Aplicación web)")
        print("4. Descargar JSON y renombrar a 'credentials.json'")
        print("5. Colocar en este directorio y ejecutar de nuevo")
