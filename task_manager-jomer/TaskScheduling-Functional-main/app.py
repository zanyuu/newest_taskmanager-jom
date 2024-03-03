from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

# SQLite database file path
DB_PATH = 'tasks.db'

# Function to create a database connection
def create_connection():
    return sqlite3.connect(DB_PATH)

# Function to execute a query and fetch all rows
def execute_query(query, params=(), commit=False):
    with create_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchall()

        if commit:
            conn.commit()

    return result

# Function to insert a new task
def insert_task(task_name, catID, date_time, priority):
    query = "INSERT INTO tasks (task_name, catID, date_time, priority) VALUES (?, ?, ?, ?)"
    params = (task_name, catID, date_time, priority)
    execute_query(query, params, commit=True)

# Function to update a task
def update_task(task_id, task_name, catID, date_time, priority):
    query = "UPDATE tasks SET task_name=?, catID=?, date_time=?, priority=? WHERE ID=?"
    params = (task_name, catID, date_time, priority, task_id)
    execute_query(query, params, commit=True)

# Function to delete a task
def delete_task(task_id):
    query = "DELETE FROM tasks WHERE ID=?"
    params = (task_id,)
    execute_query(query, params, commit=True)

# Function to fetch all tasks with joined information
def get_all_tasks_with_info():
    query = """
    SELECT tasks.ID, tasks.task_name, category.category, tasks.date_time, priority.Level
    FROM tasks
    JOIN category ON tasks.catID = category.catID
    JOIN priority ON tasks.priority = priority.prioID
    """
    tasks = execute_query(query)
    formatted_tasks = [(task[0], task[1], task[2], datetime.strptime(task[3], "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %I:%M %p"), task[4]) for task in tasks]
    return formatted_tasks

# Function to fetch all categories
def get_all_categories():
    query = "SELECT catID, category FROM category"
    categories = execute_query(query)
    return [category[1] for category in categories]

# Function to fetch all priorities
def get_all_priorities():
    query = "SELECT prioID, Level FROM priority"
    priorities = execute_query(query)
    return [priority[1] for priority in priorities]

# Function to insert a new task with category and priority
def insert_task_with_category_priority(task_name, category, date_time, priority):
    existing_category = execute_query("SELECT catID FROM category WHERE category=?", (category,))

    if not existing_category:
        execute_query("INSERT INTO category (category) VALUES (?)", (category,), commit=True)

    catID = execute_query("SELECT catID FROM category WHERE category=?", (category,))[0][0]
    prioID = execute_query("SELECT prioID FROM priority WHERE Level=?", (priority,))[0][0]

    insert_query = "INSERT INTO tasks (task_name, catID, date_time, priority) VALUES (?, ?, ?, ?)"
    params = (task_name, catID, date_time, prioID)
    execute_query(insert_query, params, commit=True)

# Function to delete a category
def delete_category(category):
    execute_query("DELETE FROM category WHERE category=?", (category,), commit=True)

# Helper function for common request processing
def process_request(request, *args):
    if request.method == 'POST':
        return args + tuple(request.form[arg] for arg in args)
    return args

# Function to handle database transactions
def transaction_handler(query, params=(), commit=False):
    return lambda conn: execute_query(query, params, commit)

# Function to compose multiple functions
def compose(*functions):
    return lambda x: reduce(lambda v, f: f(v), functions, x)

# Flask routes
@app.route('/')
def index():
    tasks = get_all_tasks_with_info()
    categories = get_all_categories()
    priority = get_all_priorities()
    return render_template('index.html', tasks=tasks, categories=categories, priority=priority)

# Update the function call in your add_task route
@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        task_name = request.form['task_name']
        category = request.form.get('category')
        date_time = request.form['date_time']
        priority = request.form['priority']

        # Update the function call with the correct number of arguments
        insert_task_with_category_priority(task_name, category, date_time, priority)

        return redirect(url_for('index'))

    # Fetch existing categories and priorities for the dropdowns
    categories = get_all_categories()
    priorities = get_all_priorities()

    return render_template('add_task.html', categories=categories, priorities=priorities)


@app.route('/edit_task/<int:task_id>')
def edit_task(task_id):
    task, categories, priorities = execute_query("SELECT * FROM tasks WHERE ID=?", (task_id,))[0], get_all_categories(), get_all_priorities()
    return render_template('edit.html', task=task, categories=categories, priorities=priorities)

@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task_route(task_id):
    if request.method == 'POST':
        task_name = request.form['task_name']
        category = request.form['category']
        date_time = request.form['date_time']
        priority = request.form['priority']

        catID = execute_query("SELECT catID FROM category WHERE category=?", (category,))[0][0]
        prioID = execute_query("SELECT prioID FROM priority WHERE Level=?", (priority,))[0][0]

        update_task(task_id, task_name, catID, date_time, prioID)

    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task_route(task_id):
    delete_task(task_id)
    return redirect(url_for('index'))

@app.route('/add_category', methods=['POST'])
def add_category():
    new_category = request.form['new_category']

    # Check if the category already exists
    existing_category = execute_query("SELECT catID FROM category WHERE category=?", (new_category,))

    if not existing_category:
        # If the category doesn't exist, insert it into the category table
        execute_query("INSERT INTO category (category) VALUES (?)", (new_category,), commit=True)

    # You can return a response if needed
    return "Category added successfully"


@app.route('/delete_category', methods=['POST'])
def delete_category_route():
    category_to_delete = request.form['delete_category']
    if execute_query("SELECT catID FROM category WHERE category=?", (category_to_delete,)):
        delete_category(category_to_delete)
        return redirect(url_for('index'))
    return "Category does not exist", 404

if __name__ == '__main__':
    app.run(debug=True)
