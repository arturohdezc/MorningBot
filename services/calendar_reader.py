import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = None
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Google credentials file not found: {credentials_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)

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