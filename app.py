from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, session
from transformers import pipeline
from cryptography.fernet import Fernet
import pyotp
import pyttsx3
import speech_recognition as sr
from googletrans import Translator
from gingerit.gingerit import GingerIt
from plyer import notification
import asyncio

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Task Reminder Variables
tasks = {}
task_id_counter = 1

# Speech-to-text and Translation Initialization
recognizer = sr.Recognizer()
translator = Translator()
engine = pyttsx3.init()

# Hugging Face GPT-2 Model for AI Content
generator = pipeline('text-generation', model='gpt2')

# Encryption Key for Password Storage
key = Fernet.generate_key()
cipher_suite = Fernet(key)
users = {'user1': cipher_suite.encrypt(b'secure_password').decode()}

# Scheduler for Task Reminders
scheduler = BackgroundScheduler()

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

scheduler.add_job(check_due_tasks, 'interval', minutes=1)
scheduler.start()

# Real-time Translation Function
async def real_time_translation():
    print("Starting Hindi-to-English real-time translation. Speak in Hindi.")
    while True:
        try:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Listening...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                hindi_text = recognizer.recognize_google(audio, language='hi-IN')
                print(f"Recognized Hindi: {hindi_text}")

                translation = translator.translate(hindi_text, src='hi', dest='en')
                print(f"English Translation: {translation.text}")

                engine.say(translation.text)
                engine.runAndWait()
        except Exception as e:
            print(f"Error: {str(e)}")

# Grammar Correction Function
def grammar_correction(text):
    parser = GingerIt()
    return parser.parse(text)['result']

# AI Content Generation
def generate_ai_content(topic):
    prompt = f"Generate a speech or lecture content on the topic: {topic}"
    result = generator(prompt, max_length=500, num_return_sequences=1)
    return result[0]['generated_text'].strip()

# Flask Routes
@app.route('/')
def home():
    return render_template('index.html', tasks=tasks)

@app.route('/generate', methods=['POST'])
def generate():
    topic = request.form['topic']
    type_of_speech = request.form['type_of_speech']

    ai_content = generate_ai_content(topic)
    template = {
        'public': 'This is a public speech on {{ topic }}. The goal is to engage and motivate the audience...',
        'private': 'This is a private lecture for a select audience on {{ topic }}. The content should be detailed and factual...'
    }.get(type_of_speech, 'Public speech template not found.')

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
        totp = pyotp.TOTP('base32secret3232')
        if totp.verify(otp):
            return redirect(url_for('home'))
        return "Invalid OTP"

    totp = pyotp.TOTP('base32secret3232')
    otp = totp.now()
    return render_template('two_factor.html', otp=otp)

@app.route('/add_task', methods=['POST'])
def add_task_route():
    global task_id_counter
    title = request.form['title']
    due_date = request.form['due_date']
    priority = request.form['priority']
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
    except Exception as e:
        return f"Error: {str(e)}"
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

if __name__ == '__main__':
    app.run(debug=True)