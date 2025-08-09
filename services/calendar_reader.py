import os
import json
import base64
from datetime import datetime, timedelta
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """Get authenticated Google Calendar service - Render compatible (headless)"""
    creds = None
    
    # Try to load from multi-account tokens first (for Render)
    try:
        tokens_b64 = os.getenv('MULTI_ACCOUNT_TOKENS_BASE64')
        if tokens_b64:
            tokens_json = base64.b64decode(tokens_b64).decode()
            tokens_data = json.loads(tokens_json)
            
            # Use first available account for calendar
            for account_email, token_data in tokens_data.items():
                if token_data.get('token') and 'calendar.readonly' in str(token_data.get('scopes', [])):
                    creds = Credentials(
                        token=token_data.get("token"),
                        refresh_token=token_data.get("refresh_token"),
                        token_uri=token_data.get("token_uri"),
                        client_id=token_data.get("client_id"),
                        client_secret=token_data.get("client_secret"),
                        scopes=token_data.get("scopes"),
                    )
                    print(f"✅ Using calendar credentials from {account_email}")
                    break
    except Exception as e:
        print(f"⚠️ Could not load from MULTI_ACCOUNT_TOKENS_BASE64: {e}")
    
    # Fallback to local token file (for development)
    if not creds:
        token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                print(f"✅ Using calendar credentials from {token_path}")
            except Exception as e:
                print(f"⚠️ Could not load from {token_path}: {e}")
    
    # Refresh if needed (headless compatible)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            print("✅ Calendar credentials refreshed successfully")
        except Exception as e:
            print(f"⚠️ Could not refresh calendar credentials: {e}")
            return None
    
    if not creds or not creds.valid:
        print("⚠️ No valid calendar credentials available")
        print("📋 Make sure MULTI_ACCOUNT_TOKENS_BASE64 is set with calendar.readonly scope")
        return None
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        print("✅ Calendar service created successfully")
        return service
    except Exception as e:
        print(f"❌ Error creating calendar service: {e}")
        return None

async def fetch_todays_events() -> List[Dict]:
    """
    Fetch today's calendar events
    
    Returns:
        List of today's events
    """
    try:
        service = get_calendar_service()
        
        # Calculate today's date range
        today = datetime.now()
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Format for Google Calendar API
        time_min = today_start.isoformat() + 'Z'
        time_max = today_end.isoformat() + 'Z'
        
        # Get events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=20,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Format start time
            start_formatted = ""
            if 'T' in start:  # DateTime format
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                start_formatted = start_dt.strftime('%H:%M')
            else:  # Date format (all-day event)
                start_formatted = "Todo el día"
            
            formatted_events.append({
                'id': event.get('id', ''),
                'summary': event.get('summary', 'Sin título'),
                'description': event.get('description', ''),
                'start': start_formatted,
                'start_raw': start,
                'end': end,
                'location': event.get('location', ''),
                'attendees': event.get('attendees', []),
                'creator': event.get('creator', {}),
                'organizer': event.get('organizer', {}),
                'status': event.get('status', 'confirmed')
            })
        
        return formatted_events
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return []