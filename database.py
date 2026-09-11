import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')

def get_db_connection():
    """Establish and return a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables and seed default categories/data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT NOT NULL,
            icon TEXT NOT NULL
        )
    ''')

    # Create Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'General',
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            subtasks TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed initial categories if empty
    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ('Work', '#6366f1', 'briefcase'),
            ('Personal', '#ec4899', 'user'),
            ('Study', '#8b5cf6', 'book-open'),
            ('Fitness', '#10b981', 'activity'),
            ('General', '#64748b', 'folder')
        ]
        cursor.executemany(
            'INSERT INTO categories (name, color, icon) VALUES (?, ?, ?)',
            default_categories
        )

    # Seed initial demo tasks if empty
    cursor.execute('SELECT COUNT(*) FROM tasks')
    if cursor.fetchone()[0] == 0:
        today_str = datetime.now().strftime('%Y-%m-%d')
        sample_tasks = [
            (
                'Complete Full Stack To-Do Project',
                'Implement backend REST API, SQLite database, dynamic UI, and validation error handling.',
                'Work',
                'High',
                'in-progress',
                today_str,
                json.dumps([
                    {'id': 1, 'title': 'Design SQLite database schema', 'completed': True},
                    {'id': 2, 'title': 'Build Flask REST API endpoints', 'completed': True},
                    {'id': 3, 'title': 'Create modern glassmorphism frontend', 'completed': False},
                    {'id': 4, 'title': 'Add form validation and notifications', 'completed': False}
                ])
            ),
            (
                'Review Weekly Goals & Fitness Plan',
                'Plan workout routines for the upcoming week and buy groceries.',
                'Fitness',
                'Medium',
                'pending',
                today_str,
                json.dumps([
                    {'id': 1, 'title': 'Morning 5k Run', 'completed': False},
                    {'id': 2, 'title': 'Meal prep for 5 days', 'completed': False}
                ])
            ),
            (
                'Read Chapter 4 of Web Architecture',
                'Focus on RESTful API best practices and client-server state decoupling.',
                'Study',
                'Low',
                'completed',
                today_str,
                json.dumps([])
            )
        ]
        cursor.executemany(
            '''INSERT INTO tasks (title, description, category, priority, status, due_date, subtasks)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            sample_tasks
        )

    conn.commit()
    conn.close()

def format_task_row(row):
    """Convert a database row into a clean serializable dictionary."""
    if not row:
        return None
    task_dict = dict(row)
    # Parse subtasks JSON string into Python list
    try:
        task_dict['subtasks'] = json.loads(task_dict.get('subtasks') or '[]')
    except (json.JSONDecodeError, TypeError):
        task_dict['subtasks'] = []
    return task_dict

def get_all_tasks(category=None, priority=None, status=None, search=None, sort_by='created_at'):
    """Fetch tasks with optional filtering and sorting."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM tasks WHERE 1=1'
    params = []

    if category and category != 'All':
        query += ' AND category = ?'
        params.append(category)

    if priority and priority != 'All':
        query += ' AND priority = ?'
        params.append(priority)

    if status and status != 'All':
        query += ' AND status = ?'
        params.append(status)

    if search:
        query += ' AND (title LIKE ? OR description LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param])

    # Sorting
    if sort_by == 'due_date':
        query += ' ORDER BY CASE WHEN due_date IS NULL OR due_date = "" THEN 1 ELSE 0 END, due_date ASC'
    elif sort_by == 'priority':
        query += ''' ORDER BY CASE priority
                        WHEN 'Urgent' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        WHEN 'Low' THEN 4
                        ELSE 5 END ASC'''
    elif sort_by == 'title':
        query += ' ORDER BY title ASC'
    else:  # default created_at
        query += ' ORDER BY created_at DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [format_task_row(row) for row in rows]

def get_task_by_id(task_id):
    """Fetch a single task by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return format_task_row(row)

def create_task(title, description='', category='General', priority='Medium', status='pending', due_date='', subtasks=None):
    """Insert a new task into the database."""
    if subtasks is None:
        subtasks = []
    
    subtasks_json = json.dumps(subtasks)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO tasks (title, description, category, priority, status, due_date, subtasks)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (title.strip(), description.strip(), category, priority, status, due_date, subtasks_json)
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_task_by_id(new_id)

def update_task(task_id, title, description='', category='General', priority='Medium', status='pending', due_date='', subtasks=None):
    """Update existing task details."""
    if subtasks is None:
        subtasks = []
        
    subtasks_json = json.dumps(subtasks)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''UPDATE tasks
           SET title = ?, description = ?, category = ?, priority = ?, status = ?, due_date = ?, subtasks = ?, updated_at = ?
           WHERE id = ?''',
        (title.strip(), description.strip(), category, priority, status, due_date, subtasks_json, now_str, task_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected == 0:
        return None
    return get_task_by_id(task_id)

def update_task_status(task_id, status):
    """Update only status of a task."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?',
        (status, now_str, task_id)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected == 0:
        return None
    return get_task_by_id(task_id)

def delete_task(task_id):
    """Delete a task by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def get_all_categories():
    """Fetch all category items."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categories ORDER BY name ASC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_category(name, color='#64748b', icon='folder'):
    """Add a custom category."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO categories (name, color, icon) VALUES (?, ?, ?)',
            (name.strip(), color, icon)
        )
        conn.commit()
        cat_id = cursor.lastrowid
        conn.close()
        return {'id': cat_id, 'name': name.strip(), 'color': color, 'icon': icon}
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_task_stats():
    """Calculate summary statistics for dashboard metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in-progress'")
    in_progress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    pending = cursor.fetchone()[0]

    today_str = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE due_date != '' AND due_date < ? AND status != 'completed'",
        (today_str,)
    )
    overdue = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM tasks WHERE due_date = ? AND status != 'completed'",
        (today_str,)
    )
    due_today = cursor.fetchone()[0]

    # Category breakdown
    cursor.execute('SELECT category, COUNT(*) as count FROM tasks GROUP BY category')
    cat_counts = {row['category']: row['count'] for row in cursor.fetchall()}

    # Priority breakdown
    cursor.execute('SELECT priority, COUNT(*) as count FROM tasks GROUP BY priority')
    prio_counts = {row['priority']: row['count'] for row in cursor.fetchall()}

    conn.close()

    completion_rate = round((completed / total * 100) if total > 0 else 0, 1)

    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'pending': pending,
        'overdue': overdue,
        'due_today': due_today,
        'completion_rate': completion_rate,
        'category_breakdown': cat_counts,
        'priority_breakdown': prio_counts
    }
