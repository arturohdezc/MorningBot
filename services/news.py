import asyncio
import feedparser
from typing import List, Dict

async def fetch_news_from_rss(rss_urls: List[str]) -> List[Dict]:
    """
    Fetch news from RSS feeds
    
    Args:
        rss_urls: List of RSS feed URLs
    
    Returns:
        List of news items
    """
    news_items = []
    
    # Default RSS feeds if none provided
    if not rss_urls:
        rss_urls = [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.reuters.com/reuters/topNews"
        ]
    
    try:
        # Fetch feeds in parallel
        tasks = []
        for url in rss_urls:
            tasks.append(fetch_single_feed(url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                news_items.extend(result)
            elif isinstance(result, Exception):
                print(f"Error fetching RSS feed: {result}")
        
        return news_items[:20]  # Limit to 20 items
        
    except Exception as e:
        print(f"Error in fetch_news_from_rss: {e}")
        return []

async def fetch_single_feed(url: str) -> List[Dict]:
    """Fetch a single RSS feed"""
    try:
        # Run feedparser in thread pool since it's blocking
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)
        
        items = []
        for entry in feed.entries[:10]:  # Limit per feed
            items.append({
                'title': entry.get('title', 'No title'),
                'summary': entry.get('summary', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'source': feed.feed.get('title', 'Unknown')
            })
        
        return items
        
    except Exception as e:
        print(f"Error fetching feed {url}: {e}")
        return []