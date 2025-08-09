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

# Target accounts to read from - Configure via environment variable
TARGET_ACCOUNTS = [
    "user1@example.com",
    "user2@example.com", 
    "user3@example.com",
    "user4@example.com",
    "user5@example.com",
]


def load_account_credentials() -> Dict[str, Credentials]:
    """Load credentials for all configured accounts"""
    tokens_file = "multi_account_tokens.json"
    account_credentials = {}
    tokens_data = {}

    # Try to load from environment variable first (for Render deployment)
    tokens_b64 = os.getenv('MULTI_ACCOUNT_TOKENS_BASE64')
    if tokens_b64:
        try:
            import base64
            tokens_json = base64.b64decode(tokens_b64).decode()
            tokens_data = json.loads(tokens_json)
            
            # Also save to file for compatibility
            with open(tokens_file, 'w') as f:
                json.dump(tokens_data, f, indent=2)
                
            print(f"✅ Tokens loaded from environment variable (Render deployment)")
        except Exception as e:
            print(f"⚠️ Error loading from environment: {e}")
            tokens_data = {}
    
    # Fallback to file if environment variable failed
    if not tokens_data and os.path.exists(tokens_file):
        try:
            with open(tokens_file, "r") as f:
                tokens_data = json.load(f)
            print(f"✅ Tokens loaded from file: {tokens_file}")
        except Exception as e:
            print(f"❌ Error loading from file: {e}")
            return {}
    
    if not tokens_data:
        print(f"⚠️ No multi-account tokens found in environment or file")
        return {}

        print(f"🔍 Found {len(tokens_data)} accounts in tokens file")

        for account_email, token_data in tokens_data.items():
            print(f"📧 Processing account: {account_email}")

            # Validate token data
            required_fields = [
                "token",
                "refresh_token",
                "token_uri",
                "client_id",
                "client_secret",
            ]
            missing_fields = [
                field for field in required_fields if not token_data.get(field)
            ]

            if missing_fields:
                print(f"⚠️ Account {account_email} missing fields: {missing_fields}")
                continue

            # Create credentials object
            try:
                creds = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes"),
                )

                account_credentials[account_email] = creds
                print(f"✅ Successfully loaded credentials for {account_email}")
                print(f"🔐 Scopes: {token_data.get('scopes', [])}")

            except Exception as cred_error:
                print(
                    f"❌ Error creating credentials for {account_email}: {cred_error}"
                )
                continue

        print(f"✅ Total loaded credentials: {len(account_credentials)} accounts")
        return account_credentials

    except Exception as e:
        print(f"❌ Error loading account credentials: {e}")
        import traceback

        traceback.print_exc()
        return {}


def get_gmail_service_for_account(account_email: str) -> Optional[object]:
    """Get Gmail service for specific account"""
    account_credentials = load_account_credentials()

    if account_email not in account_credentials:
        print(f"⚠️ No credentials found for account: {account_email}")
        return None

    try:
        creds = account_credentials[account_email]

        # Check and refresh token if needed
        print(f"🔍 Checking token status for {account_email}")
        print(f"🔍 Token expired: {creds.expired}")
        print(f"🔍 Has refresh token: {bool(creds.refresh_token)}")

        if creds.expired and creds.refresh_token:
            print(f"🔄 Refreshing expired token for {account_email}")
            try:
                from google.auth.transport.requests import Request

                creds.refresh(Request())
                print(f"✅ Token refreshed successfully for {account_email}")

                # Save updated token
                save_updated_credentials(account_email, creds)
            except Exception as refresh_error:
                print(
                    f"❌ Failed to refresh token for {account_email}: {refresh_error}"
                )
                return None
        elif creds.expired:
            print(
                f"❌ Token expired for {account_email} and no refresh token available"
            )
            return None

        return build("gmail", "v1", credentials=creds)

    except Exception as e:
        print(f"❌ Error creating Gmail service for {account_email}: {e}")
        return None


def save_updated_credentials(account_email: str, creds: Credentials):
    """Save updated credentials after refresh"""
    tokens_file = "multi_account_tokens.json"

    try:
        # Load existing tokens
        if os.path.exists(tokens_file):
            with open(tokens_file, "r") as f:
                tokens_data = json.load(f)
        else:
            tokens_data = {}

        # Update specific account
        tokens_data[account_email] = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }

        # Save back to file
        with open(tokens_file, "w") as f:
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
        print(f"🔍 Attempting to fetch emails from {account_email}")
        service = get_gmail_service_for_account(account_email)

        if not service:
            print(f"⚠️ Could not get Gmail service for {account_email}")
            return []

        print(f"✅ Gmail service obtained for {account_email}")

        # Calculate date range (today and yesterday - dynamic dates)
        now = datetime.now()
        today = now.date()
        yesterday = (now - timedelta(days=1)).date()

        # Start from yesterday 00:00:00
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        # End at today 23:59:59
        today_end = datetime.combine(today, datetime.max.time())

        # Format dates for Gmail API
        after_date = yesterday_start.strftime("%Y/%m/%d")
        before_date = today_end.strftime("%Y/%m/%d")

        # Search query for today and yesterday emails (no quantity limit)
        query = f"after:{after_date} before:{before_date}"

        print(f"📅 Searching emails for {account_email}")
        print(
            f"📅 Date range: {yesterday.strftime('%Y-%m-%d')} (ayer) to {today.strftime('%Y-%m-%d')} (hoy)"
        )
        print(f"🔍 Using query: '{query}'")

        try:
            # Get all messages from today and yesterday (no artificial limit)
            results = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=500,  # High limit to get all emails from today+yesterday
                )
                .execute()
            )

            messages = results.get("messages", [])
            print(f"📧 Found {len(messages)} messages from today and yesterday")

        except Exception as query_error:
            print(f"❌ Gmail API query failed: {query_error}")
            messages = []

        if not messages:
            print(f"ℹ️ No messages found for {account_email} from today and yesterday")
            return []

        emails = []
        total_messages = len(messages)
        print(f"📄 Processing {total_messages} messages for {account_email}")

        for i, message in enumerate(
            messages
        ):  # Process ALL messages from today+yesterday
            try:
                # Get full message
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="full")
                    .execute()
                )

                # Extract headers
                headers = msg["payload"].get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"),
                    "No Subject",
                )
                sender = next(
                    (h["value"] for h in headers if h["name"] == "From"),
                    "Unknown Sender",
                )
                to = next((h["value"] for h in headers if h["name"] == "To"), "")
                date = next((h["value"] for h in headers if h["name"] == "Date"), "")

                # Extract body (simplified)
                body = extract_message_body(msg["payload"])

                email_data = {
                    "id": message["id"],
                    "subject": subject,
                    "sender": sender,
                    "to": to,
                    "date": date,
                    "body": body[:500],  # Limit body length
                    "thread_id": msg.get("threadId", ""),
                    "labels": msg.get("labelIds", []),
                    "account": account_email,  # Real account email
                }

                emails.append(email_data)

                # Only log first few and last few to avoid spam
                if i < 3 or i >= total_messages - 3:
                    print(
                        f"📧 Email {i + 1}/{total_messages}: {subject[:50]}... from {sender[:30]}..."
                    )
                elif i == 3:
                    print(f"📧 ... processing emails 4-{total_messages - 3} ...")

            except Exception as e:
                print(
                    f"❌ Error processing email {message['id']} from {account_email}: {e}"
                )
                continue

        print(f"✅ Successfully fetched {len(emails)} emails from {account_email}")
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

        # Execute in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=12.0,  # 12 second timeout for all accounts
            )
        except asyncio.TimeoutError:
            print("⏱️ Gmail fetch timeout - using partial results")
            results = []

        # Combine results
        all_emails = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_emails.extend(result)
            elif isinstance(result, Exception):
                account = TARGET_ACCOUNTS[i] if i < len(TARGET_ACCOUNTS) else "unknown"
                print(f"❌ Error fetching from {account}: {result}")

        # Sort by date (newest first) - NO quantity limit, all emails from today+yesterday
        all_emails = sorted(all_emails, key=lambda x: x.get("date", ""), reverse=True)

        print(
            f"✅ Total emails fetched: {len(all_emails)} from {len(TARGET_ACCOUNTS)} accounts (today + yesterday)"
        )
        return all_emails

    except Exception as e:
        print(f"❌ Error in multi-account email fetch: {e}")
        return []


def extract_message_body(payload):
    """Extract message body from Gmail payload"""
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                if "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                    break
    else:
        if payload["mimeType"] == "text/plain":
            if "data" in payload["body"]:
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

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
            account = email.get("account", "unknown")
            if account not in by_account:
                by_account[account] = 0
            by_account[account] += 1

        print("📊 Emails by account:")
        for account, count in by_account.items():
            print(f"  {account}: {count} emails")

    asyncio.run(test())
