from flask import Flask, render_template, request, redirect, url_for
from functools import reduce
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Function to create a database connection
def create_connection():
    return sqlite3.connect('tasks.db')

# Function to execute a query and fetch all rows
def execute_query(conn, query, params=(), commit=False):
    cur = conn.cursor()
    cur.execute(query, params)
    result = cur.fetchall()

    if commit:
        conn.commit()

    return result

# Function to insert a new task
def insert_task(conn, task_name, catID, date_time, priority):
    query = "INSERT INTO tasks (task_name, catID, date_time, priority) VALUES (?, ?, ?, ?)"
    params = (task_name, catID, date_time, priority)
    execute_query(conn, query, params, commit=True)

# Function to update a task
def update_task(conn, task_id, task_name, catID, date_time, priority):
    query = "UPDATE tasks SET task_name=?, catID=?, date_time=?, priority=? WHERE ID=?"
    params = (task_name, catID, date_time, priority, task_id)
    execute_query(conn, query, params, commit=True)

# Function to delete a task
def delete_task(conn, task_id):
    query = "DELETE FROM tasks WHERE ID=?"
    params = (task_id,)
    execute_query(conn, query, params, commit=True)

# Function to fetch all tasks with joined information
def get_all_tasks_with_info(conn):
    query = """
    SELECT tasks.ID, tasks.task_name, category.category, tasks.date_time, priority.Level
    FROM tasks
    JOIN category ON tasks.catID = category.catID
    JOIN priority ON tasks.priority = priority.prioID
    """
    tasks = execute_query(conn, query)
    formatted_tasks = [(task[0], task[1], task[2], datetime.strptime(task[3], "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %I:%M %p"), task[4]) for task in tasks]
    return formatted_tasks

# Function to fetch all categories
def get_all_categories(conn):
    query = "SELECT catID, category FROM category"
    categories = execute_query(conn, query)
    return [category[1] for category in categories]

# Function to fetch all priorities
def get_all_priorities(conn):
    query = "SELECT prioID, Level FROM priority"
    priorities = execute_query(conn, query)
    return [priority[1] for priority in priorities]

# Function to insert a new task with category and priority
def insert_task_with_category_priority(conn, task_name, category, date_time, priority):
    existing_category = execute_query(conn, "SELECT catID FROM category WHERE category=?", (category,))

    if not existing_category:
        execute_query(conn, "INSERT INTO category (category) VALUES (?)", (category,), commit=True)

    catID = execute_query(conn, "SELECT catID FROM category WHERE category=?", (category,))[0][0]
    prioID = execute_query(conn, "SELECT prioID FROM priority WHERE Level=?", (priority,))[0][0]

    insert_query = "INSERT INTO tasks (task_name, catID, date_time, priority) VALUES (?, ?, ?, ?)"
    params = (task_name, catID, date_time, prioID)
    execute_query(conn, insert_query, params, commit=True)

# Function to delete a category
def delete_category(conn, category):
    execute_query(conn, "DELETE FROM category WHERE category=?", (category,), commit=True)

# Helper function for common request processing
def process_request(request, *args):
    if request.method == 'POST':
        return args + tuple(request.form[arg] for arg in args)
    return args

# Function to handle database transactions
def transaction_handler(conn, query, params=(), commit=False):
    return lambda conn: execute_query(conn, query, params, commit)

# Function to compose multiple functions
def compose(*functions):
    return lambda x: reduce(lambda v, f: f(v), functions, x)

# Flask routes
@app.route('/')
def index():
    conn = create_connection()
    tasks = get_all_tasks_with_info(conn)
    categories = get_all_categories(conn)
    priority = get_all_priorities(conn)
    conn.close()
    return render_template('index.html', tasks=tasks, categories=categories, priority=priority)

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if request.method == 'POST':
        conn = create_connection()
        task_name = request.form['task_name']
        category = request.form.get('category')
        date_time = request.form['date_time']
        priority = request.form['priority']
        insert_task_with_category_priority(conn, task_name, category, date_time, priority)
        conn.close()
        return redirect(url_for('index'))

    conn = create_connection()
    categories = get_all_categories(conn)
    priorities = get_all_priorities(conn)
    conn.close()
    return render_template('add_task.html', categories=categories, priorities=priorities)

@app.route('/edit_task/<int:task_id>')
def edit_task(task_id):
    conn = create_connection()
    task, categories, priorities = execute_query(conn, "SELECT * FROM tasks WHERE ID=?", (task_id,))[0], get_all_categories(conn), get_all_priorities(conn)
    conn.close()
    return render_template('edit.html', task=task, categories=categories, priorities=priorities)

@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task_route(task_id):
    if request.method == 'POST':
        conn = create_connection()
        task_name = request.form['task_name']
        category = request.form['category']
        date_time = request.form['date_time']
        priority = request.form['priority']
        catID = execute_query(conn, "SELECT catID FROM category WHERE category=?", (category,))[0][0]
        prioID = execute_query(conn, "SELECT prioID FROM priority WHERE Level=?", (priority,))[0][0]
        update_task(conn, task_id, task_name, catID, date_time, prioID)
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task_route(task_id):
    conn = create_connection()
    delete_task(conn, task_id)
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_category', methods=['POST'])
def add_category():
    conn = create_connection()
    new_category = request.form['new_category']
    existing_category = execute_query(conn, "SELECT catID FROM category WHERE category=?", (new_category,))
    if not existing_category:
        execute_query(conn, "INSERT INTO category (category) VALUES (?)", (new_category,), commit=True)
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_category', methods=['POST'])
def delete_category_route():
    conn = create_connection()
    category_to_delete = request.form['delete_category']
    if execute_query(conn, "SELECT catID FROM category WHERE category=?", (category_to_delete,)):
        delete_category(conn, category_to_delete)
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
