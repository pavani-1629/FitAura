from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
import google.generativeai as genai
from datetime import datetime

# Load environment variables
load_dotenv()

# Flask setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "defaultsecret")

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
    password = db.Column(db.String(200), nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    journal = db.Column(db.Text, nullable=True)

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# ========== Gemini AI ==========
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash")

# ========== ROUTES ==========
@app.route("/")
def home():
    return redirect("/login") if "user" not in session else redirect("/index")

@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

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
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
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
    return render_template("diet.html")  # ✅ fixed typo

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

    user_email = session["user"]["email"]

    # --- Mood quote logic ---
    latest_mood = Mood.query.filter_by(user_email=user_email).order_by(Mood.timestamp.desc()).first()
    mood = latest_mood.mood if latest_mood else "happy"

    mood_quotes = {
        "happy": [
            "Happiness is not out there, it's in you.",
            "When you're happy, you radiate positivity. Keep shining!",
            "Joy multiplies when shared. Smile more today!",
            "A cheerful heart brings its own sunshine.",
            "Celebrate every little moment of joy!"
        ],
        "motivated": [
            "Don’t wait for opportunity. Create it.",
            "The future depends on what you do today. – Gandhi",
            "Push yourself, because no one else will.",
            "Small steps every day lead to big results. Keep going!",
            "Discipline is the bridge between goals and success."
        ],
        "tired": [
            "Rest is not a waste of time. It’s how we recover and grow.",
            "Even the strongest need to recharge. Take it slow.",
            "Listen to your body — recovery is part of the journey.",
            "It’s okay to rest. You’re not quitting, you’re healing.",
            "Energy flows where rest goes."
        ],
        "stressed": [
            "Breathe. This too shall pass.",
            "One thing at a time. You’re doing better than you think.",
            "Your calm mind is your power against stress.",
            "Let go of what you can’t control and refocus your energy.",
            "Stress is a signal to slow down, not give up."
        ],
        "relaxed": [
            "Stillness is where clarity lives.",
            "Relaxation is the key to unlocking your inner power.",
            "Peace is not a place, it’s a state of mind.",
            "The quieter you become, the more you can hear.",
            "You deserve this calm. Enjoy every second."
        ]
    }

    import random
    quote = random.choice(mood_quotes.get(mood, ["Welcome to your day! You’ve got this! 💚"]))

    # --- Water Tracker ---
    if "water_count" not in session:
        session["water_count"] = 0

    if request.method == "POST":
        if "add_water" in request.form:
            session["water_count"] += 1
        elif "reset_water" in request.form:
            session["water_count"] = 0
        else:
            # To-Do submission logic
            task = request.form.get("task")
            date = request.form.get("date")
            if task and date:
                todos = session.get("todos", [])
                todos.append({"task": task, "date": date})
                session["todos"] = todos

    water = session["water_count"]
    todos = session.get("todos", [])

    return render_template("scheduler.html", water=water, quote=quote, todos=todos)

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
            user.password = generate_password_hash(new_password)
            db.session.commit()
            return "✅ Password reset! <a href='/login'>Login</a>"
        return "❌ Email not found."
    return render_template("forgot_password.html")

# ========== INIT ==========
if __name__ == "__main__":
    print("📁 Initializing database...")
    with app.app_context():
        db.create_all()
        print("✅ Tables created!")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
