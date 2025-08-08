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
    
    # Comprehensive RSS feeds - Economy, General News, AI, Travel (Mexico, US, World)
    if not rss_urls:
        rss_urls = [
            # === ECONOMÍA ===
            # Economía México
            "https://www.eleconomista.com.mx/rss/economia.xml",
            "https://www.elfinanciero.com.mx/rss/economia/",
            "https://feeds.feedburner.com/ElUniversalMexicoEconomia",
            
            # Economía US
            "https://feeds.reuters.com/reuters/businessNews",
            "https://rss.cnn.com/rss/money_latest.rss",
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://feeds.marketwatch.com/marketwatch/topstories/",
            
            # Economía Mundial
            "https://feeds.reuters.com/reuters/globalMarketsNews",
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://www.ft.com/rss/home/global-economy",
            
            # === NOTICIAS GENERALES ===
            # México General
            "https://www.eluniversal.com.mx/rss.xml",
            "https://www.milenio.com/rss/milenio.xml",
            "https://feeds.feedburner.com/Reformacom-Nacional",
            "https://www.jornada.com.mx/rss/edicion.xml",
            "https://www.excelsior.com.mx/rss.xml",
            
            # US General
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.reuters.com/reuters/topNews",
            "https://feeds.washingtonpost.com/rss/national",
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            
            # Mundial General
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.reuters.com/reuters/worldNews",
            "https://feeds.ap.org/ap/general",
            
            # === INTELIGENCIA ARTIFICIAL ===
            "https://feeds.feedburner.com/oreilly/radar/ai",
            "https://feeds.feedburner.com/venturebeat/SZYF",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.artificialintelligence-news.com/feed/",
            "https://feeds.feedburner.com/TheAiReport",
            
            # === VIAJES ===
            "https://feeds.feedburner.com/lonelyplanet/news",
            "https://feeds.feedburner.com/NatGeoTravelNews",
            "https://rss.cnn.com/rss/travel.rss",
            "https://feeds.skift.com/skift",
            "https://www.travelandleisure.com/syndication/feed"
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
        
        # Organize and limit news items
        organized_news = organize_news_by_category(news_items)
        return organized_news[:30]  # Increased limit for comprehensive coverage
        
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
        for entry in feed.entries[:5]:  # Limit per feed to manage volume
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