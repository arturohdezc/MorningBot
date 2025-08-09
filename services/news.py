import asyncio
import feedparser
from typing import List, Dict

def organize_news_by_category(news_items: List[Dict]) -> List[Dict]:
    """
    Organize news items by category and prioritize important topics
    """
    categorized = {
        'economia': [],
        'ia': [],
        'viajes': [],
        'mexico': [],
        'us': [],
        'mundial': [],
        'general': []
    }
    
    # Keywords for categorization
    economia_keywords = ['economía', 'economy', 'business', 'mercado', 'market', 'financial', 'finanzas', 'peso', 'dollar', 'inflation', 'inflación']
    ia_keywords = ['ai', 'artificial intelligence', 'inteligencia artificial', 'machine learning', 'chatgpt', 'openai', 'tech', 'tecnología']
    viajes_keywords = ['travel', 'viaje', 'tourism', 'turismo', 'vacation', 'vacaciones', 'airline', 'aerolínea', 'hotel']
    mexico_keywords = ['méxico', 'mexico', 'mexican', 'mexicano', 'amlo', 'cdmx']
    us_keywords = ['united states', 'estados unidos', 'america', 'american', 'washington', 'biden', 'trump']
    
    for item in news_items:
        title_lower = item.get('title', '').lower()
        summary_lower = item.get('summary', '').lower()
        source_lower = item.get('source', '').lower()
        text = f"{title_lower} {summary_lower} {source_lower}"
        
        # Categorize by keywords
        if any(keyword in text for keyword in economia_keywords):
            categorized['economia'].append(item)
        elif any(keyword in text for keyword in ia_keywords):
            categorized['ia'].append(item)
        elif any(keyword in text for keyword in viajes_keywords):
            categorized['viajes'].append(item)
        elif any(keyword in text for keyword in mexico_keywords):
            categorized['mexico'].append(item)
        elif any(keyword in text for keyword in us_keywords):
            categorized['us'].append(item)
        else:
            # Check if it's world news by source
            if any(source in source_lower for source in ['bbc', 'reuters', 'ap news']):
                categorized['mundial'].append(item)
            else:
                categorized['general'].append(item)
    
    # Prioritize and combine (economy first, then AI, travel, regional news)
    organized = []
    organized.extend(categorized['economia'][:8])  # Max 8 economy news
    organized.extend(categorized['ia'][:4])        # Max 4 AI news
    organized.extend(categorized['viajes'][:3])    # Max 3 travel news
    organized.extend(categorized['mexico'][:5])    # Max 5 Mexico news
    organized.extend(categorized['us'][:4])        # Max 4 US news
    organized.extend(categorized['mundial'][:4])   # Max 4 world news
    organized.extend(categorized['general'][:2])   # Max 2 general news
    
    return organized

async def fetch_news_from_rss(rss_urls: List[str]) -> List[Dict]:
    """
    Fetch news from RSS feeds
    
    Args:
        rss_urls: List of RSS feed URLs
    
    Returns:
        List of news items
    """
    news_items = []
    
    # Reliable RSS feeds - Start with most reliable ones
    if not rss_urls:
        rss_urls = [
            # === MOST RELIABLE FEEDS ===
            "https://feeds.bbci.co.uk/news/rss.xml",  # BBC News
            "https://feeds.reuters.com/reuters/topNews",  # Reuters
            "https://rss.cnn.com/rss/edition.rss",  # CNN
            
            # === ECONOMÍA ===
            "https://feeds.reuters.com/reuters/businessNews",  # Reuters Business
            "https://feeds.bbci.co.uk/news/business/rss.xml",  # BBC Business
            "https://rss.cnn.com/rss/money_latest.rss",  # CNN Money
            
            # === TECH/AI ===
            "https://techcrunch.com/feed/",  # TechCrunch
            "https://feeds.feedburner.com/venturebeat/SZYF",  # VentureBeat
            
            # === MÉXICO ===
            "https://www.eluniversal.com.mx/rss.xml",  # El Universal
            "https://www.milenio.com/rss/milenio.xml",  # Milenio
            
            # === VIAJES ===
            "https://rss.cnn.com/rss/travel.rss",  # CNN Travel
            
            # === BACKUP FEEDS (if above work) ===
            "https://feeds.reuters.com/reuters/worldNews",
            "https://www.eleconomista.com.mx/rss/economia.xml",
            "https://feeds.ap.org/ap/general",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
        ]
    
    try:
        print(f"📰 Starting to fetch {len(rss_urls)} RSS feeds")
        
        # Fetch feeds in parallel
        tasks = []
        for url in rss_urls:
            tasks.append(fetch_single_feed(url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_feeds = 0
        failed_feeds = 0
        
        for i, result in enumerate(results):
            if isinstance(result, list):
                news_items.extend(result)
                if result:
                    successful_feeds += 1
                    print(f"✅ Feed {i+1}: {len(result)} items")
                else:
                    print(f"⚠️ Feed {i+1}: 0 items")
            elif isinstance(result, Exception):
                failed_feeds += 1
                print(f"❌ Feed {i+1} failed: {result}")
        
        print(f"📊 RSS Summary: {successful_feeds} successful, {failed_feeds} failed, {len(news_items)} total items")
        
        # Organize and limit news items
        organized_news = organize_news_by_category(news_items)
        print(f"📋 Organized news: {len(organized_news)} items after categorization")
        return organized_news[:30]  # Increased limit for comprehensive coverage
        
    except Exception as e:
        print(f"Error in fetch_news_from_rss: {e}")
        return []

async def fetch_single_feed(url: str) -> List[Dict]:
    """Fetch a single RSS feed"""
    try:
        # Run feedparser in thread pool since it's blocking
        loop = asyncio.get_event_loop()
        feed = await asyncio.wait_for(
            loop.run_in_executor(None, feedparser.parse, url),
            timeout=5.0  # 5 second timeout per feed
        )
        
        # Check if feed was parsed successfully
        if not hasattr(feed, 'entries') or not feed.entries:
            print(f"⚠️ No entries found in feed: {url}")
            return []
        
        # Check for feed errors
        if hasattr(feed, 'bozo') and feed.bozo:
            print(f"⚠️ Feed parsing warning for {url}: {getattr(feed, 'bozo_exception', 'Unknown error')}")
        
        items = []
        for entry in feed.entries[:5]:  # Limit per feed to manage volume
            items.append({
                'title': entry.get('title', 'No title'),
                'summary': entry.get('summary', ''),
                'link': entry.get('link', ''),
                'published': entry.get('published', ''),
                'source': feed.feed.get('title', 'Unknown')
            })
        
        print(f"✅ Fetched {len(items)} items from {url[:50]}...")
        return items
        
    except asyncio.TimeoutError:
        print(f"⏱️ Timeout fetching feed: {url}")
        return []
    except Exception as e:
        print(f"❌ Error fetching feed {url}: {e}")
        return []