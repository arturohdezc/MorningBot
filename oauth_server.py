#!/usr/bin/env python3
"""
OAuth Server for Multi-Account Gmail Authentication
Handles OAuth flow for multiple Google accounts
"""

import os
import json
import asyncio
from typing import Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import uvicorn

app = FastAPI(title="Gmail Multi-Account OAuth Server")

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks'
]

# Store for OAuth flows (in production, use Redis or database)
oauth_flows: Dict[str, Flow] = {}
account_tokens: Dict[str, dict] = {}

def get_oauth_config():
    """Get OAuth configuration from environment or file"""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
    
    with open(credentials_path, 'r') as f:
        return json.load(f)

def get_redirect_uri():
    """Get redirect URI for OAuth"""
    base_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
    return f"{base_url}/oauth2/callback"

@app.get("/")
async def root():
    """Root endpoint with setup instructions"""
    return HTMLResponse("""
    <html>
        <head><title>Gmail Multi-Account OAuth</title></head>
        <body>
            <h1>🤖 Telegram Bot - Gmail OAuth Setup</h1>
            <h2>Configurar Cuentas Gmail:</h2>
            <p>Para cada cuenta que quieras agregar, haz clic en el enlace correspondiente:</p>
            <ul>
                <li><a href="/auth/arturohcenturion@gmail.com">arturohcenturion@gmail.com</a></li>
                <li><a href="/auth/tlapalerialavictoria@gmail.com">tlapalerialavictoria@gmail.com</a></li>
                <li><a href="/auth/arturo@nowgrowpro.com">arturo@nowgrowpro.com</a></li>
                <li><a href="/auth/determinarte@gmail.com">determinarte@gmail.com</a></li>
                <li><a href="/auth/arturohdez.92@gmail.com">arturohdez.92@gmail.com</a></li>
            </ul>
            <hr>
            <h3>Estado de Autenticación:</h3>
            <p><a href="/status">Ver estado de todas las cuentas</a></p>
        </body>
    </html>
    """)

@app.get("/auth/{account_email}")
async def start_oauth(account_email: str):
    """Start OAuth flow for specific account"""
    try:
        oauth_config = get_oauth_config()
        
        # Create OAuth flow
        flow = Flow.from_client_config(
            oauth_config,
            scopes=SCOPES,
            redirect_uri=get_redirect_uri()
        )
        
        # Store flow with account identifier
        flow_id = f"flow_{account_email}"
        oauth_flows[flow_id] = flow
        
        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=account_email  # Pass account email in state
        )
        
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting OAuth: {str(e)}")

@app.get("/oauth2/callback")
async def oauth_callback(request: Request):
    """Handle OAuth callback"""
    try:
        # Get parameters from callback
        code = request.query_params.get('code')
        state = request.query_params.get('state')  # This is the account email
        error = request.query_params.get('error')
        
        if error:
            return HTMLResponse(f"<h1>❌ Error de OAuth</h1><p>{error}</p>")
        
        if not code or not state:
            return HTMLResponse("<h1>❌ Error</h1><p>Faltan parámetros de OAuth</p>")
        
        account_email = state
        flow_id = f"flow_{account_email}"
        
        if flow_id not in oauth_flows:
            return HTMLResponse("<h1>❌ Error</h1><p>Flujo OAuth no encontrado</p>")
        
        # Complete OAuth flow
        flow = oauth_flows[flow_id]
        flow.fetch_token(code=code)
        
        # Store credentials
        credentials = flow.credentials
        account_tokens[account_email] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        # Save to file
        await save_account_tokens()
        
        # Clean up flow
        del oauth_flows[flow_id]
        
        return HTMLResponse(f"""
        <html>
            <head><title>✅ OAuth Completado</title></head>
            <body>
                <h1>✅ Autenticación Exitosa</h1>
                <p><strong>Cuenta:</strong> {account_email}</p>
                <p>La cuenta ha sido configurada correctamente.</p>
                <p><a href="/">← Volver al inicio</a></p>
                <p><a href="/status">Ver estado de todas las cuentas</a></p>
            </body>
        </html>
        """)
        
    except Exception as e:
        return HTMLResponse(f"<h1>❌ Error en callback</h1><p>{str(e)}</p>")

@app.get("/status")
async def get_status():
    """Show authentication status for all accounts"""
    await load_account_tokens()
    
    html = """
    <html>
        <head><title>Estado de Cuentas</title></head>
        <body>
            <h1>📊 Estado de Autenticación</h1>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>Cuenta</th>
                    <th>Estado</th>
                    <th>Última Actualización</th>
                </tr>
    """
    
    target_accounts = [
        "arturohcenturion@gmail.com",
        "tlapalerialavictoria@gmail.com", 
        "arturo@nowgrowpro.com",
        "determinarte@gmail.com",
        "arturohdez.92@gmail.com"
    ]
    
    for account in target_accounts:
        if account in account_tokens:
            status = "✅ Autenticado"
            last_update = "Configurado"
        else:
            status = "❌ No autenticado"
            last_update = f'<a href="/auth/{account}">Configurar ahora</a>'
        
        html += f"""
                <tr>
                    <td>{account}</td>
                    <td>{status}</td>
                    <td>{last_update}</td>
                </tr>
        """
    
    html += """
            </table>
            <br>
            <p><a href="/">← Volver al inicio</a></p>
        </body>
    </html>
    """
    
    return HTMLResponse(html)

async def save_account_tokens():
    """Save account tokens to file"""
    tokens_file = "multi_account_tokens.json"
    with open(tokens_file, 'w') as f:
        json.dump(account_tokens, f, indent=2)
    print(f"✅ Tokens guardados en {tokens_file}")

async def load_account_tokens():
    """Load account tokens from file"""
    global account_tokens
    tokens_file = "multi_account_tokens.json"
    
    if os.path.exists(tokens_file):
        with open(tokens_file, 'r') as f:
            account_tokens = json.load(f)
        print(f"✅ Tokens cargados desde {tokens_file}")

@app.on_event("startup")
async def startup_event():
    """Load tokens on startup"""
    await load_account_tokens()
    print("🚀 OAuth Server iniciado")
    print(f"📧 Cuentas configuradas: {len(account_tokens)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)