#!/usr/bin/env python3
"""
OAuth Server for Multi-Account Gmail Authentication
Handles OAuth flow for multiple Google accounts
"""

import os
import json
import base64
import asyncio
from typing import Dict, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import uvicorn

app = FastAPI(title="Gmail Multi-Account OAuth Server")

# Setup Google credentials for Render deployment
def setup_google_credentials_for_oauth():
    """Decode Google credentials from environment variables for OAuth server"""
    try:
        # Decode credentials.json from base64 if available
        credentials_b64 = os.getenv('CREDENTIALS_JSON_BASE64')
        if credentials_b64:
            credentials_data = base64.b64decode(credentials_b64).decode('utf-8')
            with open('credentials.json', 'w') as f:
                f.write(credentials_data)
            print("✅ OAuth: credentials.json decoded from environment")
        else:
            print("⚠️ OAuth: CREDENTIALS_JSON_BASE64 not found in environment")
            
    except Exception as e:
        print(f"❌ OAuth: Could not decode Google credentials: {e}")

# Setup credentials when module loads
setup_google_credentials_for_oauth()

# OAuth configuration
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/tasks'
]

# Store for OAuth flows - persisted to file for Render
oauth_flows: Dict[str, Flow] = {}
account_tokens: Dict[str, dict] = {}

def save_oauth_flow(flow_id: str, flow_data: dict):
    """Save OAuth flow data to file"""
    flows_file = "oauth_flows.json"
    flows = {}
    
    if os.path.exists(flows_file):
        try:
            with open(flows_file, 'r') as f:
                flows = json.load(f)
        except:
            flows = {}
    
    flows[flow_id] = flow_data
    
    with open(flows_file, 'w') as f:
        json.dump(flows, f, indent=2)

def load_oauth_flow(flow_id: str) -> dict:
    """Load OAuth flow data from file"""
    flows_file = "oauth_flows.json"
    
    if not os.path.exists(flows_file):
        return None
    
    try:
        with open(flows_file, 'r') as f:
            flows = json.load(f)
        return flows.get(flow_id)
    except:
        return None

def delete_oauth_flow(flow_id: str):
    """Delete OAuth flow data from file"""
    flows_file = "oauth_flows.json"
    
    if not os.path.exists(flows_file):
        return
    
    try:
        with open(flows_file, 'r') as f:
            flows = json.load(f)
        
        if flow_id in flows:
            del flows[flow_id]
            
        with open(flows_file, 'w') as f:
            json.dump(flows, f, indent=2)
    except:
        pass

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
        
        # Save flow data to file for persistence
        flow_data = {
            'client_config': oauth_config,
            'scopes': SCOPES,
            'redirect_uri': get_redirect_uri(),
            'account_email': account_email
        }
        save_oauth_flow(flow_id, flow_data)
        
        # Generate authorization URL with forced refresh token
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent screen to get refresh token
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
        
        # Try to get flow from memory first, then from file
        flow = oauth_flows.get(flow_id)
        
        if not flow:
            # Try to load from file
            flow_data = load_oauth_flow(flow_id)
            if not flow_data:
                return HTMLResponse("<h1>❌ Error</h1><p>Flujo OAuth no encontrado. Intenta de nuevo desde el inicio.</p>")
            
            # Recreate flow from saved data
            flow = Flow.from_client_config(
                flow_data['client_config'],
                scopes=flow_data['scopes'],
                redirect_uri=flow_data['redirect_uri']
            )
            oauth_flows[flow_id] = flow
        
        # Complete OAuth flow
        flow.fetch_token(code=code)
        
        # Store credentials
        credentials = flow.credentials
        
        # Validate that we have refresh_token
        if not credentials.refresh_token:
            print(f"⚠️ No refresh_token received for {account_email}")
            return HTMLResponse(f"""
            <html>
                <head><title>⚠️ Error de OAuth</title></head>
                <body>
                    <h1>⚠️ Error: No se obtuvo refresh_token</h1>
                    <p><strong>Cuenta:</strong> {account_email}</p>
                    <p>Google no proporcionó un refresh_token. Esto puede pasar si:</p>
                    <ul>
                        <li>Ya autorizaste esta app antes</li>
                        <li>No se forzó la pantalla de consentimiento</li>
                    </ul>
                    <p><strong>Solución:</strong></p>
                    <ol>
                        <li>Ve a <a href="https://myaccount.google.com/permissions" target="_blank">Google Account Permissions</a></li>
                        <li>Revoca el acceso a "Arturo Multi-Account Bot"</li>
                        <li><a href="/auth/{account_email}">Intenta autorizar de nuevo</a></li>
                    </ol>
                </body>
            </html>
            """)
        
        account_tokens[account_email] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        print(f"✅ Stored complete credentials for {account_email} (including refresh_token)")
        
        # Save to file
        await save_account_tokens()
        
        # Clean up flow from memory and file
        if flow_id in oauth_flows:
            del oauth_flows[flow_id]
        delete_oauth_flow(flow_id)
        
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
                    <th>Acciones</th>
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
            actions = f'<a href="/test/{account}">🧪 Probar Gmail</a>'
        else:
            status = "❌ No autenticado"
            actions = f'<a href="/auth/{account}">🔧 Configurar</a>'
        
        html += f"""
                <tr>
                    <td>{account}</td>
                    <td>{status}</td>
                    <td>{actions}</td>
                </tr>
        """
    
    html += f"""
            </table>
            <br>
            <p><strong>Total cuentas configuradas:</strong> {len(account_tokens)}</p>
            <p><a href="/">← Volver al inicio</a></p>
            <p><a href="/debug">🔍 Ver información de debug</a></p>
        </body>
    </html>
    """
    
    return HTMLResponse(html)

@app.get("/test/{account_email}")
async def test_gmail_account(account_email: str):
    """Test Gmail connectivity for specific account"""
    try:
        # Import here to avoid circular imports
        from services.gmail_multi_account import fetch_emails_from_specific_account
        
        print(f"🧪 Testing Gmail connectivity for {account_email}")
        emails = await fetch_emails_from_specific_account(account_email)
        
        return {
            "account": account_email,
            "status": "success" if emails else "no_emails",
            "email_count": len(emails),
            "emails": emails[:3] if emails else [],  # Show first 3 emails
            "message": f"Found {len(emails)} emails" if emails else "No emails found in last 7 days"
        }
        
    except Exception as e:
        return {
            "account": account_email,
            "status": "error",
            "error": str(e),
            "message": f"Error testing {account_email}: {str(e)}"
        }

@app.get("/debug")
async def debug_info():
    """Show debug information"""
    await load_account_tokens()
    
    debug_data = {
        "total_accounts": len(account_tokens),
        "accounts": list(account_tokens.keys()),
        "environment_variable_set": bool(os.getenv('MULTI_ACCOUNT_TOKENS_BASE64')),
        "file_exists": os.path.exists("multi_account_tokens.json")
    }
    
    return debug_data

async def save_account_tokens():
    """Save account tokens to file and environment variable for persistence"""
    tokens_file = "multi_account_tokens.json"
    
    # Save to file (temporary)
    with open(tokens_file, 'w') as f:
        json.dump(account_tokens, f, indent=2)
    print(f"✅ Tokens guardados en {tokens_file}")
    
    # Also encode and save to environment variable for persistence
    try:
        import base64
        tokens_json = json.dumps(account_tokens)
        tokens_b64 = base64.b64encode(tokens_json.encode()).decode()
        
        # In production, you would set this as an environment variable
        # For now, we'll save it to a persistent file that can be manually copied
        with open('tokens_backup.txt', 'w') as f:
            f.write(f"MULTI_ACCOUNT_TOKENS_BASE64={tokens_b64}\n")
        
        print(f"💾 Backup tokens saved - copy to Render environment variable:")
        print(f"MULTI_ACCOUNT_TOKENS_BASE64={tokens_b64[:50]}...")
        
    except Exception as e:
        print(f"⚠️ Could not create backup: {e}")

async def load_account_tokens():
    """Load account tokens from environment variable or file"""
    global account_tokens
    tokens_file = "multi_account_tokens.json"
    
    # Try to load from environment variable first (persistent)
    tokens_b64 = os.getenv('MULTI_ACCOUNT_TOKENS_BASE64')
    if tokens_b64:
        try:
            import base64
            tokens_json = base64.b64decode(tokens_b64).decode()
            account_tokens = json.loads(tokens_json)
            
            # Also save to file for other services
            with open(tokens_file, 'w') as f:
                json.dump(account_tokens, f, indent=2)
                
            print(f"✅ Tokens cargados desde variable de entorno (persistente)")
            print(f"📧 Cuentas configuradas: {len(account_tokens)}")
            return
        except Exception as e:
            print(f"⚠️ Error loading from environment: {e}")
    
    # Fallback to file
    if os.path.exists(tokens_file):
        with open(tokens_file, 'r') as f:
            account_tokens = json.load(f)
        print(f"✅ Tokens cargados desde {tokens_file}")
    else:
        print("ℹ️ No tokens found - accounts need to be configured")

@app.on_event("startup")
async def startup_event():
    """Load tokens on startup"""
    await load_account_tokens()
    print("🚀 OAuth Server iniciado")
    print(f"📧 Cuentas configuradas: {len(account_tokens)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)