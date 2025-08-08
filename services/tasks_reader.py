import os
import pickle
from datetime import datetime
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_google_tasks_service():
    """Get authenticated Google Tasks service"""
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
    
    return build('tasks', 'v1', credentials=creds)

async def fetch_pending_tasks() -> List[Dict]:
    """
    Fetch pending tasks from Google Tasks (existing function - preserved)
    
    Returns:
        List of pending tasks
    """
    try:
        service = get_google_tasks_service()
        
        # Get all task lists
        results = service.tasklists().list().execute()
        task_lists = results.get('items', [])
        
        all_tasks = []
        
        for task_list in task_lists:
            # Get tasks from each list
            tasks_result = service.tasks().list(
                tasklist=task_list['id'],
                showCompleted=False,
                showHidden=False
            ).execute()
            
            tasks = tasks_result.get('items', [])
            
            for task in tasks:
                # Only include tasks that are due today or overdue
                if task.get('due'):
                    due_date = datetime.fromisoformat(task['due'].replace('Z', '+00:00')).date()
                    today = datetime.now().date()
                    
                    if due_date <= today:
                        all_tasks.append({
                            'id': task['id'],
                            'title': task.get('title', ''),
                            'notes': task.get('notes', ''),
                            'due': task.get('due'),
                            'status': task.get('status', 'needsAction'),
                            'list_id': task_list['id'],
                            'list_name': task_list.get('title', 'Default')
                        })
                else:
                    # Tasks without due date are considered pending
                    all_tasks.append({
                        'id': task['id'],
                        'title': task.get('title', ''),
                        'notes': task.get('notes', ''),
                        'due': None,
                        'status': task.get('status', 'needsAction'),
                        'list_id': task_list['id'],
                        'list_name': task_list.get('title', 'Default')
                    })
        
        return all_tasks
        
    except Exception as e:
        print(f"Error fetching Google Tasks: {e}")
        return []

async def create_google_task(title: str, notes: str = "", due: Optional[datetime] = None) -> Optional[str]:
    """
    Create task in Google Tasks and return Google task ID
    
    Args:
        title: Task title
        notes: Task notes
        due: Due date (optional)
    
    Returns:
        Google task ID if successful, None otherwise
    """
    try:
        service = get_google_tasks_service()
        
        # Get the default task list (first one)
        results = service.tasklists().list().execute()
        task_lists = results.get('items', [])
        
        if not task_lists:
            print("No task lists found in Google Tasks")
            return None
        
        default_list_id = task_lists[0]['id']
        
        # Prepare task data
        task_body = {
            'title': title,
            'notes': notes
        }
        
        if due:
            # Google Tasks expects RFC 3339 format
            task_body['due'] = due.isoformat()
        
        # Create the task
        result = service.tasks().insert(
            tasklist=default_list_id,
            body=task_body
        ).execute()
        
        return result.get('id')
        
    except Exception as e:
        print(f"Error creating Google Task: {e}")
        return None

async def sync_local_to_google(local_task: Dict) -> Optional[str]:
    """
    Create Google Tasks copy of local task
    
    Args:
        local_task: Local task dictionary
    
    Returns:
        Google task ID if successful, None otherwise
    """
    # Only sync if SYNC_GOOGLE_TASKS is enabled
    if os.getenv("SYNC_GOOGLE_TASKS", "false").lower() != "true":
        return None
    
    try:
        title = local_task.get('title', 'Untitled Task')
        notes = local_task.get('notes', '')
        
        # Parse due date if present
        due = None
        if local_task.get('due'):
            try:
                due = datetime.fromisoformat(local_task['due'].replace('Z', '+00:00'))
            except:
                pass
        
        # Add note about local origin
        if notes:
            notes += f"\n\n[Sincronizado desde bot local - ID: {local_task.get('id', 'unknown')}]"
        else:
            notes = f"[Sincronizado desde bot local - ID: {local_task.get('id', 'unknown')}]"
        
        return await create_google_task(title, notes, due)
        
    except Exception as e:
        print(f"Error syncing local task to Google: {e}")
        return None

def update_google_task_status(google_task_id: str, list_id: str, completed: bool = True) -> bool:
    """
    Update Google Task status (mark as completed/incomplete)
    
    Args:
        google_task_id: Google task ID
        list_id: Google task list ID
        completed: Whether to mark as completed
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service = get_google_tasks_service()
        
        task_body = {
            'status': 'completed' if completed else 'needsAction'
        }
        
        if completed:
            task_body['completed'] = datetime.now().isoformat()
        
        service.tasks().update(
            tasklist=list_id,
            task=google_task_id,
            body=task_body
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Error updating Google Task status: {e}")
        return False

def delete_google_task(google_task_id: str, list_id: str) -> bool:
    """
    Delete Google Task
    
    Args:
        google_task_id: Google task ID
        list_id: Google task list ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service = get_google_tasks_service()
        
        service.tasks().delete(
            tasklist=list_id,
            task=google_task_id
        ).execute()
        
        return True
        
    except Exception as e:
        print(f"Error deleting Google Task: {e}")
        return False