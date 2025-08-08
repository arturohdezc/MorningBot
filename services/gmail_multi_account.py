#!/usr/bin/env python3
"""
Multi-Account Gmail Reader with Real OAuth
Supports multiple Google accounts with independent authentication
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64

# Target accounts to read from
TARGET_ACCOUNTS = [
    "arturohcenturion@gmail.com",
    "tlapalerialavictoria@gmail.com", 
    "arturo@nowgrowpro.com",
    "determinarte@gmail.com",
    "arturohdez.92@gmail.com"
]

def load_account_credentials() -> Dict[str, Credentials]:
    """Load credentials for all configured accounts"""
    tokens_file = "multi_account_tokens.json"
    account_credentials = {}
    
    if not os.path.exists(tokens_file):
        print(f"⚠️ Multi-account tokens file not found: {tokens_file}")
        return {}
    
    try:
        with open(tokens_file, 'r') as f:
            tokens_data = json.load(f)
        
        for account_email, token_data in tokens_data.items():
            # Create credentials object
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            account_credentials[account_email] = creds
            
        print(f"✅ Loaded credentials for {len(account_credentials)} accounts")
        return account_credentials
        
    except Exception as e:
        print(f"❌ Error loading account credentials: {e}")
        return {}

def get_gmail_service_for_account(account_email: str) -> Optional[object]:
    """Get Gmail service for specific account"""
    account_credentials = load_account_credentials()
    
    if account_email not in account_credentials:
        print(f"⚠️ No credentials found for account: {account_email}")
        return None
    
    try:
        creds = account_credentials[account_email]
        
        # Refresh token if needed
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            
            # Save updated token
            save_updated_credentials(account_email, creds)
        
        return build('gmail', 'v1', credentials=creds)
        
    except Exception as e:
        print(f"❌ Error creating Gmail service for {account_email}: {e}")
        return None

def save_updated_credentials(account_email: str, creds: Credentials):
    """Save updated credentials after refresh"""
    tokens_file = "multi_account_tokens.json"
    
    try:
        # Load existing tokens
        if os.path.exists(tokens_file):
            with open(tokens_file, 'r') as f:
                tokens_data = json.load(f)
        else:
            tokens_data = {}
        
        # Update specific account
        tokens_data[account_email] = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
            'expiry': creds.expiry.isoformat() if creds.expiry else None
        }
        
        # Save back to file
        with open(tokens_file, 'w') as f:
            json.dump(tokens_data, f, indent=2)
            
        print(f"✅ Updated credentials for {account_email}")
        
    except Exception as e:
        print(f"❌ Error saving updated credentials: {e}")

async def fetch_emails_from_specific_account(account_email: str) -> List[Dict]:
    """
    Fetch emails from a specific Gmail account
    
    Args:
        account_email: Gmail account email address
    
    Returns:
        List of email data from the account
    """
    try:
        service = get_gmail_service_for_account(account_email)
        
        if not service:
            print(f"⚠️ Could not get Gmail service for {account_email}")
            return []
        
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
            userId='me',  # Always 'me' for the authenticated account
            q=query,
            maxResults=50  # Limit per account
        ).execute()
        
        messages = results.get('messages', [])
        
        emails = []
        for message in messages[:50]:  # Limit per account
            try:
                # Get full message
                msg = service.users().messages().get(
                    userId='me',
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
                    'account': account_email  # Real account email
                })
                
            except Exception as e:
                print(f"Error processing email {message['id']} from {account_email}: {e}")
                continue
        
        print(f"✅ Fetched {len(emails)} emails from {account_email}")
        return emails
        
    except Exception as e:
        print(f"❌ Error fetching emails from {account_email}: {e}")
        return []

async def fetch_all_accounts_emails() -> List[Dict]:
    """
    Fetch emails from all configured accounts in parallel
    
    Returns:
        List of all emails from all accounts
    """
    try:
        # Create tasks for all target accounts
        tasks = []
        for account_email in TARGET_ACCOUNTS:
            tasks.append(fetch_emails_from_specific_account(account_email))
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_emails = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_emails.extend(result)
            elif isinstance(result, Exception):
                account = TARGET_ACCOUNTS[i] if i < len(TARGET_ACCOUNTS) else 'unknown'
                print(f"❌ Error fetching from {account}: {result}")
        
        # Sort by date (newest first) and limit total
        all_emails = sorted(all_emails, key=lambda x: x.get('date', ''), reverse=True)
        limited_emails = all_emails[:200]  # Limit total emails
        
        print(f"✅ Total emails fetched: {len(limited_emails)} from {len(TARGET_ACCOUNTS)} accounts")
        return limited_emails
        
    except Exception as e:
        print(f"❌ Error in multi-account email fetch: {e}")
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

# Backward compatibility function
async def fetch_yesterdays_emails() -> List[Dict]:
    """
    Backward compatibility function for existing code
    Uses multi-account implementation
    """
    return await fetch_all_accounts_emails()

if __name__ == "__main__":
    # Test the multi-account functionality
    async def test():
        emails = await fetch_all_accounts_emails()
        print(f"📧 Total emails: {len(emails)}")
        
        # Group by account
        by_account = {}
        for email in emails:
            account = email.get('account', 'unknown')
            if account not in by_account:
                by_account[account] = 0
            by_account[account] += 1
        
        print("📊 Emails by account:")
        for account, count in by_account.items():
            print(f"  {account}: {count} emails")
    
    asyncio.run(test())