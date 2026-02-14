import requests
import time
from datetime import date, timedelta

base_url = "http://127.0.0.1:3000"

# User data
# users = [
#     {
#         "id": "usr_1",
#         "name": "Alice Johnson",
#         "timezone": "America/New_York",
#         "created_at": "2024-01-15"
#     },
#     {
#         "id": "usr_2",
#         "name": "Bob Smith",
#         "timezone": "America/Los_Angeles",
#         "created_at": "2024-02-20"
#     },
#     {
#         "id": "usr_3",
#         "name": "Carol Williams",
#         "timezone": "Europe/London",
#         "created_at": "2024-03-10"
#     }
# ]

# Board data
boards = [
    {
        "id": "bd_1",
        "user_id": "usr_1",
        "path": "/work",
        "depth": 1,
        "name": "Work Board",
        "color": "#3b82f6"
    },
    {
        "id": "bd_2",
        "user_id": "usr_1",
        "path": "/personal",
        "depth": 1,
        "name": "Personal Board",
        "color": "#10b981"
    },
    {
        "id": "bd_3",
        "user_id": "usr_1",
        "path": "/work/projects",
        "depth": 2,
        "name": "Projects Board",
        "color": "#f59e0b"
    },
    {
        "id": "bd_7",
        "user_id": "usr_1",
        "path": "/work/projects",
        "depth": 2,
        "name": "Other Projects Board",
        "color": "#0000ff"
    },
    {
        "id": "bd_4",
        "user_id": "usr_2",
        "path": "/home",
        "depth": 1,
        "name": "Home Board",
        "color": "#8b5cf6"
    },
    {
        "id": "bd_5",
        "user_id": "usr_2",
        "path": "/home/fitness",
        "depth": 2,
        "name": "Fitness Board",
        "color": "#ec4899"
    },
    {
        "id": "bd_6",
        "user_id": "usr_3",
        "path": "/archive",
        "depth": 1,
        "name": "Archive Board",
        "color": "#6366f1"
    }
]

# Folder data
folders = [
    {
        "id": "fld_1",
        "user_id": "usr_1",
        "path": "/work",
        "depth": 1,
        "name": "Work"
    },
    {
        "id": "fld_2",
        "user_id": "usr_1",
        "path": "/personal",
        "depth": 1,
        "name": "Personal"
    },
    {
        "id": "fld_3",
        "user_id": "usr_1",
        "path": "/work/projects",
        "depth": 2,
        "name": "Projects"
    },
    {
        "id": "fld_7",
        "user_id": "usr_1",
        "path": "/work/projects",
        "depth": 2,
        "name": "Better Projects"
    },
    {
        "id": "fld_4",
        "user_id": "usr_2",
        "path": "/home",
        "depth": 1,
        "name": "Home"
    },
    {
        "id": "fld_5",
        "user_id": "usr_2",
        "path": "/home/fitness",
        "depth": 2,
        "name": "Fitness"
    },
    {
        "id": "fld_6",
        "user_id": "usr_3",
        "path": "/archive",
        "depth": 1,
        "name": "Archive"
    }
]

# Tag data
tags = [
    {
        "id": "tag_1",
        "user_id": "usr_1",
        "name": "Urgent",
        "background_color": "#ff4444",
        "border_color": "#cc0000",
        "text_color": "#ffffff"
    },
    {
        "id": "tag_2",
        "user_id": "usr_1",
        "name": "Low Priority",
        "background_color": "#e0e0e0",
        "border_color": "#999999",
        "text_color": "#333333"
    },
    {
        "id": "tag_3",
        "user_id": "usr_2",
        "name": "Important",
        "background_color": "#ffa500",
        "border_color": "#ff8800",
        "text_color": "#000000"
    },
    {
        "id": "tag_4",
        "user_id": "usr_2",
        "name": "Personal",
        "background_color": "#4a90e2",
        "border_color": "#2e5c8a",
        "text_color": "#ffffff"
    },
    {
        "id": "tag_5",
        "user_id": "usr_3",
        "name": "Review",
        "background_color": "#9b59b6",
        "border_color": "#7d3c98",
        "text_color": "#ffffff"
    }
]

# Task data
today = date.today()
tasks = [
    {
        "id": "tsk_1",
        "board_id": "bd_1",
        "name": "Complete project proposal",
        "description": "Draft and finalize the Q1 project proposal for client review",
        "progress": "in-progress",
        "priority_level": 1,
        "due_date": (today + timedelta(days=7)).isoformat(),
        "created_at": (today - timedelta(days=3)).isoformat()
    },
    {
        "id": "tsk_2",
        "board_id": "bd_1",
        "name": "Review budget",
        "description": "Analyze and approve departmental budget for next quarter",
        "progress": "to-do",
        "priority_level": 2,
        "due_date": (today + timedelta(days=14)).isoformat(),
        "created_at": (today - timedelta(days=1)).isoformat()
    },
    {
        "id": "tsk_3",
        "board_id": "bd_2",
        "name": "Team meeting preparation",
        "description": "Prepare slides and agenda for weekly team sync",
        "progress": "done",
        "priority_level": 3,
        "due_date": (today - timedelta(days=1)).isoformat(),
        "created_at": (today - timedelta(days=5)).isoformat()
    },
    {
        "id": "tsk_4",
        "board_id": "bd_3",
        "name": "Update documentation",
        "description": "Revise user manual with latest feature updates",
        "progress": "pending",
        "priority_level": 2,
        "due_date": (today + timedelta(days=21)).isoformat(),
        "created_at": (today - timedelta(days=2)).isoformat()
    },
    {
        "id": "tsk_5",
        "board_id": "bd_4",
        "name": "Code review",
        "description": "Review pull requests from development team",
        "progress": "in-progress",
        "priority_level": 1,
        "due_date": (today + timedelta(days=2)).isoformat(),
        "created_at": today.isoformat()
    },
    {
        "id": "tsk_6",
        "board_id": "bd_5",
        "name": "Database optimization",
        "description": "Optimize queries and indexing for better performance",
        "progress": "to-do",
        "priority_level": 2,
        "due_date": (today + timedelta(days=30)).isoformat(),
        "created_at": (today - timedelta(days=4)).isoformat()
    }
]

# Event data
events = [
    {
        "id": "evt_1",
        "board_id": "bd_1",
        "start_time": (today + timedelta(days=1)).isoformat(),
        "end_time": (today + timedelta(days=1)).isoformat(),
        "event_color": "#ff6b6b",
        "is_all_day": False,
        "description": "Quarterly planning meeting with stakeholders",
        "location": "Conference Room A",
        "recurrence": None
    },
    {
        "id": "evt_2",
        "board_id": "bd_1",
        "start_time": today.isoformat(),
        "end_time": today.isoformat(),
        "event_color": "#4ecdc4",
        "is_all_day": True,
        "description": "Team building day",
        "location": "Offsite",
        "recurrence": None
    },
    {
        "id": "evt_3",
        "board_id": "bd_2",
        "start_time": (today + timedelta(days=7)).isoformat(),
        "end_time": (today + timedelta(days=7)).isoformat(),
        "event_color": "#95e1d3",
        "is_all_day": False,
        "description": "Weekly standup meeting",
        "location": "Zoom",
        "recurrence": {
            "frequency": "weekly",
            "day_of_week": ["monday", "wednesday", "friday"],
            "termination_date": (today + timedelta(days=90)).isoformat(),
            "date_start": today.isoformat()
        }
    },
    {
        "id": "evt_4",
        "board_id": "bd_3",
        "start_time": (today + timedelta(days=2)).isoformat(),
        "end_time": (today + timedelta(days=2)).isoformat(),
        "event_color": "#f38181",
        "is_all_day": False,
        "description": "Client presentation",
        "location": "Client Office",
        "recurrence": None
    },
    {
        "id": "evt_5",
        "board_id": "bd_4",
        "start_time": (today + timedelta(days=5)).isoformat(),
        "end_time": (today + timedelta(days=5)).isoformat(),
        "event_color": "#aa96da",
        "is_all_day": True,
        "description": "Company holiday",
        "location": "N/A",
        "recurrence": {
            "frequency": "yearly",
            "day_of_week": [],
            "termination_date": (today + timedelta(days=365*5)).isoformat(),
            "date_start": (today + timedelta(days=5)).isoformat()
        }
    },
    {
        "id": "evt_6",
        "board_id": "bd_5",
        "start_time": (today + timedelta(days=10)).isoformat(),
        "end_time": (today + timedelta(days=12)).isoformat(),
        "event_color": "#fcbad3",
        "is_all_day": True,
        "description": "Annual conference",
        "location": "Convention Center",
        "recurrence": None
    }
]

def check_health(endpoint, entity_name):
    """Check if endpoint is healthy and accessible"""
    health_url = f"{base_url}{endpoint}"
    try:
        response = requests.get(health_url, timeout=5)
        print(f"  ✓ {entity_name} endpoint ({endpoint}) is reachable (status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ✗ {entity_name} endpoint ({endpoint}) - Connection refused")
        return False
    except requests.exceptions.Timeout:
        print(f"  ✗ {entity_name} endpoint ({endpoint}) - Request timed out")
        return False
    except Exception as e:
        print(f"  ✗ {entity_name} endpoint ({endpoint}) - Error: {str(e)}")
        return False

def insert_data(endpoint, data_list, entity_name):
    """Helper function to insert data with error handling"""
    print(f"\n{'='*60}")
    print(f"Inserting {entity_name}")
    print(f"{'='*60}")
    
    for item in data_list:
        try:
            print(base_url + endpoint)
            response = requests.post(f"{base_url}{endpoint}", json=item)
            status_indicator = "✓" if response.status_code in [200, 201] else "✗"
            print(f"{status_indicator} POST {item['id']} → {response.status_code}")
            
            try:
                print(f"  Response: {response.json()}")
            except ValueError:
                if response.text:
                    print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error inserting {item['id']}: {str(e)}")
        
        time.sleep(0.1)

# Define endpoints and their data
endpoints_config = [
    ("/user/board", boards, "Boards"),
    ("/user/folder", folders, "Folders"),
    ("/user/tag", tags, "Tags"),
    ("/board/task", tasks, "Tasks"),
    ("/board/event", events, "Events")
]

# Insert all data
if __name__ == "__main__":
    print("Starting data insertion...")
    print(f"Base URL: {base_url}")
    
    # Health check phase
    print(f"\n{'='*60}")
    print("HEALTH CHECK")
    print(f"{'='*60}")
    
    healthy_endpoints = []
    for endpoint, data, entity_name in endpoints_config:
        if check_health(endpoint, entity_name):
            healthy_endpoints.append((endpoint, data, entity_name))
        time.sleep(0.1)
    
    # Summary of health check
    print(f"\n{'='*60}")
    print(f"Health Check Summary: {len(healthy_endpoints)}/{len(endpoints_config)} endpoints healthy")
    print(f"{'='*60}")
    
    if not healthy_endpoints:
        print("\n⚠️  No healthy endpoints found. Aborting data insertion.")
        exit(1)
    
    if len(healthy_endpoints) < len(endpoints_config):
        print("\n⚠️  Some endpoints are unhealthy. Proceeding with healthy endpoints only.")
        user_input = input("Continue? (y/n): ")
        if user_input.lower() != 'y':
            print("Aborted by user.")
            exit(0)
    
    # Data insertion phase
    print("\n" + "="*60)
    print("STARTING DATA INSERTION")
    print("="*60)
    
    for endpoint, data, entity_name in healthy_endpoints:
        insert_data(endpoint, data, entity_name)
    
    print(f"\n{'='*60}")
    print("Data insertion complete!")
    print(f"{'='*60}")