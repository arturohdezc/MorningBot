import json
import uuid
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dateutil.rrule import rrule, rrulestr
from dateutil.parser import parse as parse_date
import pytz

TASKS_DB_FILE = "tasks_db.json"

def generate_task_id() -> str:
    """Generate a human-friendly task ID"""
    import random
    import string
    
    # Generate a short, readable ID like T001, T002, etc.
    tasks_data = load_tasks()
    existing_ids = [task.get('id', '') for task in tasks_data.get('tasks', [])]
    
    # Find next available number
    counter = 1
    while f"T{counter:03d}" in existing_ids:
        counter += 1
    
    return f"T{counter:03d}"

def load_tasks() -> Dict:
    """Load tasks from JSON file"""
    try:
        if os.path.exists(TASKS_DB_FILE):
            with open(TASKS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"tasks": []}
    except Exception as e:
        print(f"Error loading tasks: {e}")
        return {"tasks": []}

def save_tasks(tasks_data: Dict) -> bool:
    """Save tasks to JSON file"""
    try:
        with open(TASKS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving tasks: {e}")
        return False

def add_task(title: str, notes: str = "", priority: str = "medium", due: Optional[datetime] = None) -> str:
    """
    Create a new task and persist to tasks_db.json
    
    Args:
        title: Task title
        notes: Optional notes
        priority: Priority level (high|medium|low)
        due: Optional due date
    
    Returns:
        Task ID
    """
    tasks_data = load_tasks()
    
    task_id = generate_task_id()
    now = datetime.now(timezone.utc).isoformat()
    
    task = {
        "id": task_id,
        "title": title,
        "notes": notes,
        "priority": priority,
        "due": due.isoformat() if due else None,
        "completed": False,
        "createdAt": now,
        "updatedAt": now,
        "source": "local",
        "rrule": None
    }
    
    tasks_data["tasks"].append(task)
    
    if save_tasks(tasks_data):
        # Try to sync to Google Tasks if enabled
        if os.getenv("SYNC_GOOGLE_TASKS", "false").lower() == "true":
            try:
                from .tasks_reader import sync_local_to_google
                sync_local_to_google(task)
            except Exception as e:
                print(f"Failed to sync to Google Tasks: {e}")
        
        return task_id
    else:
        raise Exception("Failed to save task")

def add_recurrent_task(title: str, rrule: str, notes: str = "", priority: str = "medium", start_due: Optional[datetime] = None) -> str:
    """
    Create a recurring task with RRULE validation
    
    Args:
        title: Task title
        rrule: RRULE string (e.g., "FREQ=MONTHLY;BYMONTHDAY=1")
        notes: Optional notes
        priority: Priority level (high|medium|low)
        start_due: Optional start date for recurrence
    
    Returns:
        Task ID
    """
    # Validate RRULE
    try:
        rrulestr(rrule)
    except Exception as e:
        raise ValueError(f"Invalid RRULE: {e}")
    
    tasks_data = load_tasks()
    
    task_id = generate_task_id()
    now = datetime.now(timezone.utc).isoformat()
    
    task = {
        "id": task_id,
        "title": title,
        "notes": notes,
        "priority": priority,
        "due": start_due.isoformat() if start_due else None,
        "completed": False,
        "createdAt": now,
        "updatedAt": now,
        "source": "local",
        "rrule": rrule
    }
    
    tasks_data["tasks"].append(task)
    
    if save_tasks(tasks_data):
        return task_id
    else:
        raise Exception("Failed to save recurring task")

def expand_for_today(tz: str) -> List[Dict]:
    """
    Generate recurring task instances for current date without duplicates
    
    Args:
        tz: Timezone string (e.g., "America/Mexico_City")
    
    Returns:
        List of task instances for today
    """
    tasks_data = load_tasks()
    timezone_obj = pytz.timezone(tz)
    today = datetime.now(timezone_obj).date()
    
    expanded_tasks = []
    
    for task in tasks_data["tasks"]:
        if task.get("rrule") and not task.get("completed"):
            try:
                # Parse the RRULE
                rule = rrulestr(task["rrule"])
                
                # Get start date
                if task.get("due"):
                    start_date = parse_date(task["due"]).date()
                else:
                    start_date = parse_date(task["createdAt"]).date()
                
                # Check if today matches the recurrence
                occurrences = rule.between(
                    datetime.combine(today, datetime.min.time()),
                    datetime.combine(today, datetime.max.time()),
                    inc=True
                )
                
                if occurrences or (start_date == today and rule.count is None):
                    # Create instance for today
                    instance = task.copy()
                    instance["id"] = f"{task['id']}_today"
                    instance["due"] = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone_obj).isoformat()
                    
                    # Check if we should sync to Google Tasks
                    if os.getenv("SYNC_GOOGLE_TASKS", "false").lower() == "true":
                        try:
                            from .tasks_reader import sync_local_to_google
                            sync_local_to_google(instance)
                        except Exception as e:
                            print(f"Failed to sync recurring task to Google Tasks: {e}")
                    
                    expanded_tasks.append(instance)
                    
            except Exception as e:
                print(f"Error expanding recurring task {task['id']}: {e}")
    
    return expanded_tasks

def list_today_sorted(tz: str) -> List[Dict]:
    """
    Return tasks ordered by priority (high>medium>low) then by hour
    
    Args:
        tz: Timezone string
    
    Returns:
        Sorted list of today's tasks
    """
    tasks_data = load_tasks()
    timezone_obj = pytz.timezone(tz)
    today = datetime.now(timezone_obj).date()
    
    # Get regular tasks for today
    today_tasks = []
    for task in tasks_data["tasks"]:
        if not task.get("completed") and not task.get("rrule"):
            if task.get("due"):
                due_date = parse_date(task["due"]).date()
                if due_date <= today:  # Include overdue tasks
                    today_tasks.append(task)
            else:
                # Tasks without due date are considered for today
                created_date = parse_date(task["createdAt"]).date()
                if created_date == today:
                    today_tasks.append(task)
    
    # Add expanded recurring tasks
    today_tasks.extend(expand_for_today(tz))
    
    # Priority order mapping
    priority_order = {"high": 0, "medium": 1, "low": 2}
    
    def sort_key(task):
        priority = priority_order.get(task.get("priority", "medium"), 1)
        
        # Extract hour from due date, default to 0 if no due date
        hour = 0
        if task.get("due"):
            try:
                due_dt = parse_date(task["due"])
                hour = due_dt.hour
            except:
                hour = 0
        
        return (priority, hour)
    
    return sorted(today_tasks, key=sort_key)

def complete_task(task_id: str) -> bool:
    """
    Mark task as completed in JSON and update timestamp
    
    Args:
        task_id: Task ID to complete
    
    Returns:
        True if successful, False otherwise
    """
    tasks_data = load_tasks()
    
    for task in tasks_data["tasks"]:
        if task["id"] == task_id:
            task["completed"] = True
            task["updatedAt"] = datetime.now(timezone.utc).isoformat()
            return save_tasks(tasks_data)
    
    return False