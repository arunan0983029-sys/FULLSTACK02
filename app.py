import json
import os
from flask import Flask, render_template, request, jsonify, make_response
import database as db

app = Flask(__name__, template_folder='templates', static_folder='static')

# Initialize DB tables on startup
db.init_db()

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Resource not found', 'status': 404}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error occurred', 'status': 500}), 500

@app.route('/')
def index():
    """Serve main SPA HTML page."""
    return render_template('index.html')

# ---------------------------------------------------------
# TASK REST API ENDPOINTS
# ---------------------------------------------------------

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """
    Fetch all tasks with support for filtering & sorting.
    Query params: category, priority, status, search, sort_by
    """
    category = request.args.get('category')
    priority = request.args.get('priority')
    status = request.args.get('status')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'created_at')

    tasks = db.get_all_tasks(
        category=category,
        priority=priority,
        status=status,
        search=search,
        sort_by=sort_by
    )
    return jsonify({'success': True, 'count': len(tasks), 'tasks': tasks})

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Fetch single task details by ID."""
    task = db.get_task_by_id(task_id)
    if not task:
        return jsonify({'success': False, 'error': f'Task with ID {task_id} not found'}), 404
    return jsonify({'success': True, 'task': task})

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """
    Create a new task.
    Requires JSON payload with 'title'. Optional: description, category, priority, status, due_date, subtasks
    """
    data = request.get_json() or {}
    title = data.get('title')

    # Server-side Validation
    if not title or not isinstance(title, str) or not title.strip():
        return jsonify({
            'success': False,
            'error': 'Validation Error: Task title is required and cannot be empty.'
        }), 400

    if len(title.strip()) < 3:
        return jsonify({
            'success': False,
            'error': 'Validation Error: Title must be at least 3 characters long.'
        }), 400

    priority = data.get('priority', 'Medium')
    valid_priorities = ['Low', 'Medium', 'High', 'Urgent']
    if priority not in valid_priorities:
        priority = 'Medium'

    status = data.get('status', 'pending')
    valid_statuses = ['pending', 'in-progress', 'completed']
    if status not in valid_statuses:
        status = 'pending'

    category = data.get('category', 'General')
    description = data.get('description', '')
    due_date = data.get('due_date', '')
    subtasks = data.get('subtasks', [])

    if not isinstance(subtasks, list):
        subtasks = []

    new_task = db.create_task(
        title=title,
        description=description,
        category=category,
        priority=priority,
        status=status,
        due_date=due_date,
        subtasks=subtasks
    )

    return jsonify({'success': True, 'message': 'Task created successfully', 'task': new_task}), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update task details completely."""
    data = request.get_json() or {}
    title = data.get('title')

    if not title or not isinstance(title, str) or not title.strip():
        return jsonify({
            'success': False,
            'error': 'Validation Error: Task title is required.'
        }), 400

    if len(title.strip()) < 3:
        return jsonify({
            'success': False,
            'error': 'Validation Error: Title must be at least 3 characters long.'
        }), 400

    priority = data.get('priority', 'Medium')
    valid_priorities = ['Low', 'Medium', 'High', 'Urgent']
    if priority not in valid_priorities:
        priority = 'Medium'

    status = data.get('status', 'pending')
    valid_statuses = ['pending', 'in-progress', 'completed']
    if status not in valid_statuses:
        status = 'pending'

    category = data.get('category', 'General')
    description = data.get('description', '')
    due_date = data.get('due_date', '')
    subtasks = data.get('subtasks', [])

    if not isinstance(subtasks, list):
        subtasks = []

    updated_task = db.update_task(
        task_id=task_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        status=status,
        due_date=due_date,
        subtasks=subtasks
    )

    if not updated_task:
        return jsonify({'success': False, 'error': f'Task with ID {task_id} not found'}), 404

    return jsonify({'success': True, 'message': 'Task updated successfully', 'task': updated_task})

@app.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
def update_task_status(task_id):
    """Quickly update the status of a task."""
    data = request.get_json() or {}
    status = data.get('status')

    valid_statuses = ['pending', 'in-progress', 'completed']
    if not status or status not in valid_statuses:
        return jsonify({
            'success': False,
            'error': f'Validation Error: Status must be one of {valid_statuses}'
        }), 400

    updated_task = db.update_task_status(task_id, status)
    if not updated_task:
        return jsonify({'success': False, 'error': f'Task with ID {task_id} not found'}), 404

    return jsonify({'success': True, 'message': 'Status updated', 'task': updated_task})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task."""
    success = db.delete_task(task_id)
    if not success:
        return jsonify({'success': False, 'error': f'Task with ID {task_id} not found'}), 404

    return jsonify({'success': True, 'message': f'Task {task_id} deleted successfully'})

# ---------------------------------------------------------
# CATEGORY REST API ENDPOINTS
# ---------------------------------------------------------

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Fetch all available task categories."""
    categories = db.get_all_categories()
    return jsonify({'success': True, 'categories': categories})

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create a custom user category."""
    data = request.get_json() or {}
    name = data.get('name')
    color = data.get('color', '#6366f1')
    icon = data.get('icon', 'folder')

    if not name or not isinstance(name, str) or not name.strip():
        return jsonify({'success': False, 'error': 'Category name is required'}), 400

    new_cat = db.create_category(name.strip(), color, icon)
    if not new_cat:
        return jsonify({'success': False, 'error': 'Category with this name already exists'}), 400

    return jsonify({'success': True, 'category': new_cat}), 201

# ---------------------------------------------------------
# DASHBOARD STATS & IMPORT/EXPORT API
# ---------------------------------------------------------

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard task statistics."""
    stats = db.get_task_stats()
    return jsonify({'success': True, 'stats': stats})

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export all tasks as JSON file."""
    tasks = db.get_all_tasks()
    categories = db.get_all_categories()
    export_payload = {
        'version': '1.0',
        'exported_at': db.datetime.now().isoformat(),
        'categories': categories,
        'tasks': tasks
    }
    response = make_response(jsonify(export_payload))
    response.headers['Content-Disposition'] = 'attachment; filename=taskpulse_backup.json'
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/api/import', methods=['POST'])
def import_data():
    """Import tasks from JSON list."""
    data = request.get_json() or {}
    tasks = data.get('tasks', [])
    if not isinstance(tasks, list):
        return jsonify({'success': False, 'error': 'Invalid payload format'}), 400

    imported_count = 0
    for item in tasks:
        if isinstance(item, dict) and item.get('title'):
            db.create_task(
                title=item.get('title'),
                description=item.get('description', ''),
                category=item.get('category', 'General'),
                priority=item.get('priority', 'Medium'),
                status=item.get('status', 'pending'),
                due_date=item.get('due_date', ''),
                subtasks=item.get('subtasks', [])
            )
            imported_count += 1

    return jsonify({
        'success': True,
        'message': f'Successfully imported {imported_count} tasks.'
    })

if __name__ == '__main__':
    print("Starting TaskPulse REST API server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
