from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import os
import google.generativeai as genai
from datetime import datetime
import random

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

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    task = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    completed = db.Column(db.Boolean, default=False)

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

@app.route("/bmi")
def bmi():
    return render_template("bmi.html")

@app.route("/diet")
def diet():
    return render_template("diet.html")

@app.route("/diet/general", methods=["POST"])
def diet_general():
    age = request.form["age"]
    gender = request.form["gender"]
    diet_type = request.form["diet_type"]
    goal = request.form["goal"]
    prompt = (
        f"You are a professional human dietician. Suggest a healthy {diet_type} diet plan for a {gender}, age {age}, "
        f"who wants to {goal}. The response must be clear, look real, and feel like advice from a doctor. "
        f"Avoid using asterisks (*), don't say 'as an AI', and explain step-by-step with emojis to improve clarity step by step , assume you are a doctor."
    )
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
    prompt = (
        f"You are a certified nutritionist. Suggest a complete diet plan for a {gender}, age {age}, {weight}kg, {height}cm, "
        f"who has {condition} and wants to {goal}. The recommendation should sound like it’s coming from a doctor, "
        f"be practical, step-by-step, and include clear instructions with relevant emojis. No asterisks (*) or AI-related phrases step by step and assume you are doctor."
    )
    try:
        result = model.generate_content(prompt).text
    except Exception as e:
        result = f"⚠️ Error: {e}"
    return render_template("diet_result.html", result=result)

@app.route("/mood", methods=["GET", "POST"])
def mood_tracker():
    if "user" not in session:
        return redirect("/login")

    user_email = session["user"]["email"]

    if request.method == "POST":
        selected_mood = request.form.get("mood")
        if selected_mood:
            db.session.add(Mood(user_email=user_email, mood=selected_mood))
            db.session.commit()

        # To-Do logic
        task = request.form.get("task")
        date = request.form.get("date")
        if task and date:
            db.session.add(Task(user_email=user_email, task=task, date=date))
            db.session.commit()

        # Water intake
        session["water_count"] = session.get("water_count", 0)
        if "add_water" in request.form:
            session["water_count"] += 1
        elif "reset_water" in request.form:
            session["water_count"] = 0

    latest_mood = Mood.query.filter_by(user_email=user_email).order_by(Mood.timestamp.desc()).first()
    todos = Task.query.filter_by(user_email=user_email).all()
    water = session.get("water_count", 0)

    return render_template("mood.html", mood=latest_mood.mood if latest_mood else None, todos=todos, water=water)

@app.route("/timer", methods=["GET", "POST"])
def timer():
    if request.method == "POST":
        goal = request.form["goal"]
        age = request.form["age"]
        gender = request.form["gender"]
        prompt = (
            f"You are a certified fitness trainer. Provide a detailed step-by-step plan for a {age}-year-old {gender} with the goal '{goal}'. "
            f"Ensure the advice sounds human and expert-level, not AI-generated. Use clear steps and include emojis for better understanding. Avoid using asterisks (*) and robotic tone Assume you are a doctor or fitness trainer."
        )
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
