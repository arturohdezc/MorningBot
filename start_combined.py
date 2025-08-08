#!/usr/bin/env python3
"""
Combined startup script for OAuth server and Telegram bot
Runs both services in the same process for Render deployment
"""

import os
import asyncio
import threading
import uvicorn
from oauth_server import app as oauth_app

def run_oauth_server():
    """Run OAuth server in separate thread"""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(oauth_app, host="0.0.0.0", port=port, log_level="info")

def run_telegram_bot():
    """Run Telegram bot"""
    # Import here to avoid circular imports
    import bot
    # The bot.py should have its main execution logic

async def main():
    """Main function to coordinate both services"""
    print("🚀 Starting combined OAuth + Telegram Bot server...")
    
    # Start OAuth server in background thread
    oauth_thread = threading.Thread(target=run_oauth_server, daemon=True)
    oauth_thread.start()
    
    print("✅ OAuth server started")
    print("🤖 Starting Telegram bot...")
    
    # Start Telegram bot (this will block)
    run_telegram_bot()

if __name__ == "__main__":
    asyncio.run(main())