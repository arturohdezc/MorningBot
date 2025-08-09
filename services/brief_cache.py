#!/usr/bin/env python3
"""
Brief Cache System - Progressive Brief Generation
Manages brief generation in sprints to avoid Telegram timeouts
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class BriefProgress:
    """Track brief generation progress"""
    user_id: int
    started_at: datetime
    last_updated: datetime
    status: str  # 'generating', 'completed', 'failed'
    progress_percentage: int
    
    # Data components
    news_data: Optional[Dict] = None
    emails_data: Optional[Dict] = None
    calendar_data: Optional[list] = None
    tasks_data: Optional[list] = None
    
    # Progress flags
    news_completed: bool = False
    emails_completed: bool = False
    calendar_completed: bool = False
    tasks_completed: bool = False
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['started_at'] = self.started_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        # Convert ISO strings back to datetime
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

class BriefCache:
    """Manage brief generation cache and progress"""
    
    def __init__(self, cache_file: str = "brief_cache.json"):
        self.cache_file = cache_file
        self.cache: Dict[int, BriefProgress] = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                
                for user_id_str, progress_data in data.items():
                    user_id = int(user_id_str)
                    self.cache[user_id] = BriefProgress.from_dict(progress_data)
            except Exception as e:
                print(f"⚠️ Error loading brief cache: {e}")
                self.cache = {}
    
    def save_cache(self):
        """Save cache to file"""
        try:
            data = {}
            for user_id, progress in self.cache.items():
                data[str(user_id)] = progress.to_dict()
            
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving brief cache: {e}")
    
    def start_brief_generation(self, user_id: int) -> BriefProgress:
        """Start new brief generation for user"""
        now = datetime.now()
        
        progress = BriefProgress(
            user_id=user_id,
            started_at=now,
            last_updated=now,
            status='generating',
            progress_percentage=0
        )
        
        self.cache[user_id] = progress
        self.save_cache()
        return progress
    
    def get_progress(self, user_id: int) -> Optional[BriefProgress]:
        """Get current progress for user"""
        return self.cache.get(user_id)
    
    def update_progress(self, user_id: int, **kwargs):
        """Update progress for user"""
        if user_id not in self.cache:
            return
        
        progress = self.cache[user_id]
        progress.last_updated = datetime.now()
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(progress, key):
                setattr(progress, key, value)
        
        # Calculate progress percentage
        completed_count = sum([
            progress.news_completed,
            progress.emails_completed,
            progress.calendar_completed,
            progress.tasks_completed
        ])
        progress.progress_percentage = int((completed_count / 4) * 100)
        
        # Update status
        if progress.progress_percentage == 100:
            progress.status = 'completed'
        
        self.save_cache()
    
    def is_brief_fresh(self, user_id: int, max_age_minutes: int = 30) -> bool:
        """Check if brief is fresh enough to reuse"""
        progress = self.get_progress(user_id)
        if not progress or progress.status != 'completed':
            return False
        
        age = datetime.now() - progress.last_updated
        return age.total_seconds() < (max_age_minutes * 60)
    
    def should_show_progress(self, user_id: int, timeout_seconds: int = 8) -> bool:
        """Check if we should show progress instead of waiting"""
        progress = self.get_progress(user_id)
        if not progress or progress.status != 'generating':
            return False
        
        elapsed = datetime.now() - progress.started_at
        return elapsed.total_seconds() > timeout_seconds
    
    def cleanup_old_entries(self, max_age_hours: int = 24):
        """Clean up old cache entries"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for user_id, progress in self.cache.items():
            if progress.last_updated < cutoff:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.cache[user_id]
        
        if to_remove:
            self.save_cache()
            print(f"🧹 Cleaned up {len(to_remove)} old brief cache entries")

# Global cache instance
brief_cache = BriefCache()