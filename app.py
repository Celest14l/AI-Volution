from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from plyer import notification
from flask import Flask, render_template, request, redirect, url_for, session
from transformers import pipeline
import pyotp
from cryptography.fernet import Fernet

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Task Reminder Code (In-memory storage)
tasks = {}
task_id_counter = 1

# Function to add a task
def add_task(title, due_date, priority):
    global task_id_counter
    try:
        due_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M")
        tasks[task_id_counter] = {
            "title": title,
            "due_date": due_date,
            "priority": priority,
            "notified": False,
            "completed": False
        }
        task_id_counter += 1
        return f"Task '{title}' added successfully!"
    except Exception as e:
        return f"Error: {str(e)}"

# Function to check due tasks and send notifications
def check_due_tasks():
    now = datetime.now()
    for task_id, task in tasks.items():
        if task["due_date"] <= now + timedelta(hours=1) and not task["notified"] and not task["completed"]:
            notification.notify(
                title="Task Reminder",
                message=f"Task '{task['title']}' is due in 1 hour!",
                timeout=10
            )
            task["notified"] = True

# Scheduler for notifications
scheduler = BackgroundScheduler()
scheduler.add_job(check_due_tasks, 'interval', minutes=1)
scheduler.start()

# AI Writer Code (Hugging Face GPT-2)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Dummy user data for login
users = {'user1': 'encrypted_password'}

# Set up Hugging Face pipeline (GPT-2)
generator = pipeline('text-generation', model='gpt2')

def generate_ai_content(topic):
    prompt = f"Generate a speech or lecture content on the topic: {topic}"
    result = generator(prompt, max_length=500, num_return_sequences=1)
    return result[0]['generated_text'].strip()

# Template selection for public/private speeches
def get_template(type_of_speech):
    templates = {
        'public': 'This is a public speech on {{ topic }}. The goal is to engage and motivate the audience...',
        'private': 'This is a private lecture for a select audience on {{ topic }}. The content should be detailed and factual...'
    }
    return templates.get(type_of_speech, 'Public speech template not found.')

# Routes for AI Writer
@app.route('/')
def home():
    return render_template('index.html', tasks=tasks)

@app.route('/generate', methods=['POST'])
def generate():
    topic = request.form['topic']
    type_of_speech = request.form['type_of_speech']
    
    ai_content = generate_ai_content(topic)
    template = get_template(type_of_speech)
    
    speech = template.replace('{{ topic }}', topic) + '\n' + ai_content
    return render_template('speech_result.html', speech=speech)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        stored_password = users.get(username)
        if stored_password and cipher_suite.decrypt(stored_password.encode()).decode() == password:
            session['username'] = username
            return redirect(url_for('two_factor'))
        return "Invalid login"
    return render_template('login.html')

@app.route('/two_factor', methods=['GET', 'POST'])
def two_factor():
    if request.method == 'POST':
        otp = request.form['otp']
        totp = pyotp.TOTP('base32secret3232')  # Example secret
        if totp.verify(otp):
            return redirect(url_for('home'))
        return "Invalid OTP"
    
    totp = pyotp.TOTP('base32secret3232')
    otp = totp.now()
    return render_template('two_factor.html', otp=otp)

# Task Reminder Routes
@app.route('/add_task', methods=['POST'])
def add_task_route():
    title = request.form['title']
    due_date = request.form['due_date']
    priority = request.form['priority']
    message = add_task(title, due_date, priority)
    return redirect(url_for('home'))

@app.route('/view_tasks')
def view_tasks():
    return render_template('tasks.html', tasks=tasks)

@app.route('/mark_complete/<int:task_id>')
def mark_complete(task_id):
    task = tasks.get(task_id)
    if task:
        task['completed'] = True
    return redirect(url_for('view_tasks'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if task_id in tasks:
        del tasks[task_id]
    return redirect(url_for('view_tasks'))

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
