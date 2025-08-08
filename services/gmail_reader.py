import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get authenticated Gmail service"""
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
    
    return build('gmail', 'v1', credentials=creds)

async def fetch_yesterdays_emails() -> List[Dict]:
    """
    Fetch emails from yesterday from multiple Gmail accounts (up to ~200 total)
    
    Returns:
        List of email data from all configured accounts
    """
    gmail_accounts = os.getenv("GMAIL_ACCOUNTS", "").strip()
    
    if not gmail_accounts:
        # Single account mode (backward compatibility)
        return await fetch_emails_from_account("me")
    
    # Multi-account mode
    accounts = [acc.strip() for acc in gmail_accounts.split(",") if acc.strip()]
    all_emails = []
    
    try:
        # Fetch emails from all accounts in parallel
        import asyncio
        tasks = []
        for account in accounts:
            tasks.append(fetch_emails_from_account(account))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, list):
                # Add account info to each email
                for email in result:
                    email['account'] = accounts[i] if i < len(accounts) else 'unknown'
                all_emails.extend(result)
            elif isinstance(result, Exception):
                print(f"Error fetching emails from account {accounts[i] if i < len(accounts) else 'unknown'}: {result}")
        
        # Limit total emails and sort by date
        all_emails = sorted(all_emails, key=lambda x: x.get('date', ''), reverse=True)
        return all_emails[:200]  # Limit to 200 total
        
    except Exception as e:
        print(f"Error in multi-account email fetch: {e}")
        return []

async def fetch_emails_from_account(account_id: str) -> List[Dict]:
    """
    Fetch emails from a specific Gmail account
    
    Args:
        account_id: Gmail account identifier ('me' for primary, or specific account)
    
    Returns:
        List of email data from the account
    """
    try:
        service = get_gmail_service()
        
        # Calculate yesterday's date range
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Format dates for Gmail API
        after_date = yesterday_start.strftime('%Y/%m/%d')
        before_date = yesterday_end.strftime('%Y/%m/%d')
        
        # Search query for yesterday's emails
        query = f'after:{after_date} before:{before_date}'
        
        # Get message IDs
        results = service.users().messages().list(
            userId=account_id,
            q=query,
            maxResults=100  # Limit per account to allow multiple accounts
        ).execute()
        
        messages = results.get('messages', [])
        
        emails = []
        for message in messages[:100]:  # Limit per account
            try:
                # Get full message
                msg = service.users().messages().get(
                    userId=account_id,
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract headers
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                to = next((h['value'] for h in headers if h['name'] == 'To'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Extract body (simplified)
                body = extract_message_body(msg['payload'])
                
                emails.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'to': to,
                    'date': date,
                    'body': body[:500],  # Limit body length
                    'thread_id': msg.get('threadId', ''),
                    'labels': msg.get('labelIds', []),
                    'account': account_id
                })
                
            except Exception as e:
                print(f"Error processing email {message['id']} from account {account_id}: {e}")
                continue
        
        return emails
        
    except Exception as e:
        print(f"Error fetching Gmail emails from account {account_id}: {e}")
        return []

def extract_message_body(payload):
    """Extract message body from Gmail payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
    else:
        if payload['mimeType'] == 'text/plain':
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return body