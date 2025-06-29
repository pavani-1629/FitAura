from flask import send_from_directory, Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import google.generativeai as genai
from datetime import datetime
import requests

# Load environment variables
load_dotenv()

# Flask setup
app = Flask(__name__)
app.secret_key = "6cc781732ebe1b601cf347eac6fa41f133f67981f6b87128"

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fitaura.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========== MODELS ==========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)

# ========== Gemini AI ==========
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")

# ========== OneSignal Push ==========
ONESIGNAL_API_KEY = os.getenv("ONESIGNAL_API_KEY")
ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID")

def send_push_notification(user_email, task):
    url = "https://onesignal.com/api/v1/notifications"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_API_KEY}"
    }
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "include_external_user_ids": [user_email],
        "channel_for_external_user_ids": "push",
        "headings": {"en": "⏰ Task Reminder"},
        "contents": {"en": f"Hey! It's time for: {task}"},
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"🔔 Notification sent to {user_email}: {response.status_code}")
    except Exception as e:
        print(f"❌ Push failed for {user_email}: {e}")
# ========== ROUTES ==========

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return redirect("/index")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            return "⚠️ User already exists. Please login."

        db.session.add(User(username=username, email=email, password=password))
        db.session.commit()
        session["user"] = {"username": username, "email": email}
        return redirect("/index")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session["user"] = {"username": user.username, "email": user.email}
            return redirect("/index")
        return "❌ Invalid login."
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    return render_template("profile.html", user=session["user"])

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/diet")
def diet():
    return render_template("diet.html")

@app.route("/diet/general", methods=["POST"])
def diet_general():
    age = request.form["age"]
    gender = request.form["gender"]
    diet_type = request.form["diet_type"]
    goal = request.form["goal"]
    prompt = f"Suggest a healthy {diet_type} diet plan for a {gender}, age {age}, who wants to {goal}. Step by step with emojis clearly. Don't use * and no AI-like response."
    try:
        result = model.generate_content(prompt).text
    except Exception as e:
        result = f"⚠️ Error: {e}"
    return render_template("diet_result.html", result=result)

@app.route("/diet/condition", methods=["POST"])
def diet_condition():
    age = request.form["age"]
    gender = request.form["gender"]
    weight = request.form["weight"]
    height = request.form["height"]
    goal = request.form["goal"]
    condition = request.form["condition"]
    prompt = f"Suggest a diet for a {gender}, age {age}, {weight}kg, {height}cm, has {condition}, wants to {goal}. Doctor-style, emojis, clear and not AI-like."
    try:
        result = model.generate_content(prompt).text
    except Exception as e:
        result = f"⚠️ Error: {e}"
    return render_template("diet_result.html", result=result)

@app.route("/bmi")
def bmi():
    return render_template("bmi.html")

@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        task = request.form["task"]
        date = request.form["date"]
        time_ = request.form["time"]
        user_email = session["user"]["email"]

        db.session.add(Schedule(task=task, date=date, time=time_, user_email=user_email))
        db.session.commit()
        return redirect("/schedule")

    user_tasks = Schedule.query.filter_by(user_email=session["user"]["email"]).all()
    return render_template("schedule.html", tasks=user_tasks)

@app.route("/delete-task", methods=["POST"])
def delete_task():
    if "user" not in session:
        return redirect("/login")

    task_id = request.form.get("task_id")
    if task_id:
        task = Schedule.query.filter_by(id=task_id).first()
        if task and task.user_email == session["user"]["email"]:
            db.session.delete(task)
            db.session.commit()
    return redirect("/schedule")

@app.route("/timer", methods=["GET", "POST"])
def timer():
    if request.method == "POST":
        goal = request.form["goal"]
        age = request.form["age"]
        gender = request.form["gender"]
        prompt = f"Suggest fitness steps for a {age}-year-old {gender} with goal '{goal}'. Step-by-step with emojis, clear, doctor-style. Not AI-generated looking."
        try:
            result = model.generate_content(prompt).text
        except Exception as e:
            result = f"⚠️ Error: {e}"
        return render_template("timer.html", result=result, goal=goal, age=age, gender=gender)

    return render_template("timer.html")

@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    user_message = request.get_json().get("message", "")
    try:
        reply = model.generate_content(user_message).text
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"❌ Error: {e}"})

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        new_password = request.form["new_password"]
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = new_password
            db.session.commit()
            return "✅ Password reset! <a href='/login'>Login</a>"
        return "❌ Email not found."
    return render_template("forgot_password.html")


@app.route("/check-schedule")
def check_schedule():
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    print(f"🔍 Checking tasks for: {date_str} {time_str}")

    tasks = Schedule.query.filter_by(date=date_str, time=time_str).all()
    for task in tasks:
        print(f"🔔 Sending notification for: {task.task}")
        send_push_notification(task.user_email, task.task)

    return "✅ Checked schedule and sent notifications (if matched)."

@app.route('/OneSignalSDKWorker.js')
def onesignal_sdk_worker():
    return send_from_directory('.', 'OneSignalSDKWorker.js')

# ========== INIT ==========
if __name__ == "__main__":
    print("📁 Initializing database...")
    with app.app_context():
        db.create_all()
        print("✅ Tables created!")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
