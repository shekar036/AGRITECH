import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
from PIL import Image
import io
from collections import Counter
from transformers import pipeline
import google.generativeai as genai
import json

app = Flask(__name__)
app.secret_key = "secret-key"
CORS(app)

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===== Model Setup =====
MODEL_NAME = "google/efficientnet-b0"
GEMINI_API_KEY = "AIzaSyCPes8fcjbEmxAZFTpa9HvMc-lqZb00jO8"
genai.configure(api_key=GEMINI_API_KEY)

pipe = pipeline("image-classification", model=MODEL_NAME)

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config={
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    },
)

# ===== Database Setup =====
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        disease TEXT,
        file_path TEXT,
        timestamp TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        name TEXT NOT NULL,
        message TEXT NOT NULL,
        rating INTEGER DEFAULT 0,
        timestamp TEXT DEFAULT (datetime('now','localtime'))
    )""")

    conn.commit()
    conn.close()

init_db()

def update_feedback_table():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    c.execute("PRAGMA table_info(feedback)")
    existing_columns = [row[1] for row in c.fetchall()]

    if "rating" not in existing_columns:
        c.execute("ALTER TABLE feedback ADD COLUMN rating INTEGER DEFAULT 0")

    if "timestamp" not in existing_columns:
        c.execute("ALTER TABLE feedback ADD COLUMN timestamp TEXT")
        c.execute("UPDATE feedback SET timestamp = datetime('now', 'localtime') WHERE timestamp IS NULL")

    conn.commit()
    conn.close()

update_feedback_table()

# ===== Utilities =====
def format_disease_name(name):
    return name.replace("_", " ").title()

def get_disease_info(disease_name):
    try:
        response = model.generate_content([
            "input: Cure and cause of disease",
            "output: {\n  \"disease_name\": \"Bell Pepper with Bacterial Spot\",\n  \"causes\": [\n    \"Bacterial Spot is caused by the bacterium Xanthomonas campestris pv. vesicatoria.\",\n    \"It spreads through rain, wind, and contaminated tools or equipment.\"\n  ],\n  \"cure\": [\n    \"Use copper-based fungicides.\",\n    \"Remove infected material.\"\n  ],\n  \"prevention\": [\n    \"Use disease-free seeds.\",\n    \"Disinfect tools.\"\n  ],\n  \"recommendations\": [\n    \"Monitor regularly.\",\n    \"Ensure good drainage.\"\n  ]\n}",
            f"input: Cure and cause of {disease_name}",
            "output:"
        ])
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"[Gemini Error] {e}")
        return {
            "causes": ["Information not available"],
            "cure": ["Information not available"],
            "prevention": ["Information not available"],
            "recommendations": ["Information not available"]
        }

# ===== Routes =====
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/detect")
def detect():
    return render_template("Agri_tech.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_email"] = user[2]
            session["user_name"] = user[1]
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Email already registered.")
        finally:
            conn.close()
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        file = request.files["file"]
        image = Image.open(io.BytesIO(file.read()))
        result = pipe(image)[0]

        disease = format_disease_name(result["label"])
        confidence = round(result["score"], 4)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        image.save(file_path)

        user_email = session.get("user_email", "guest")

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO history (user_email, disease, file_path, timestamp) VALUES (?, ?, ?, ?)",
                  (user_email, disease, file_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

        info = get_disease_info(disease)

        return jsonify({
            "disease": disease,
            "confidence": confidence,
            "causes": info["causes"],
            "cure": info["cure"],
            "prevention": info["prevention"],
            "recommendations": info["recommendations"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history")
def history():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    per_page = 15
    page = int(request.args.get("page", 1))
    offset = (page - 1) * per_page

    user_history = []
    if "user_email" in session:
        user_email = session["user_email"]
        c.execute("""SELECT id, user_email, disease, file_path, timestamp 
                     FROM history 
                     WHERE user_email=? 
                     ORDER BY timestamp DESC""", (user_email,))
        rows = c.fetchall()
        user_history = [
            {
                "id": row[0],
                "user": row[1],
                "disease": row[2],
                "image_filename": os.path.basename(row[3]),
                "timestamp": row[4]
            } for row in rows
        ]

    c.execute("SELECT COUNT(*) FROM history")
    total_records = c.fetchone()[0]
    total_pages = (total_records + per_page - 1) // per_page

    c.execute("""SELECT id, user_email, disease, file_path, timestamp 
                 FROM history 
                 ORDER BY timestamp DESC 
                 LIMIT ? OFFSET ?""", (per_page, offset))
    rows = c.fetchall()

    c.execute("SELECT email, name FROM users")
    user_map = dict(c.fetchall())

    total_history = [
        {
            "id": row[0],
            "user": user_map.get(row[1], "Guest") if row[1] != "guest" else "Guest",
            "disease": row[2],
            "image_filename": os.path.basename(row[3]),
            "timestamp": row[4]
        } for row in rows
    ]

    conn.close()

    return render_template("history.html",
                           user_history=user_history,
                           total_history=total_history,
                           current_page=page,
                           total_pages=total_pages)

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        name = request.form["name"]
        message = request.form["feedword"]
        rating = int(request.form.get("rating", 0))
        email = session.get("user_email", "guest")

        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        if email == "guest":
            c.execute("SELECT timestamp FROM feedback WHERE user_email='guest' ORDER BY id DESC LIMIT 1")
            last = c.fetchone()
            if last and last[0]:
                try:
                    last_time = datetime.strptime(last[0], "%Y-%m-%d %H:%M:%S")
                    if datetime.now() - last_time < timedelta(seconds=60):
                        conn.close()
                        return render_template("feedback.html", success=False, error="⚠️ Please wait before submitting again.")
                except ValueError:
                    pass

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO feedback (user_email, name, message, rating, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (email, name, message, rating, timestamp))
        conn.commit()
        conn.close()
        return render_template("feedback.html", success=True)

    return render_template("feedback.html", success=False)

@app.route("/feedback-history")
def feedback_history():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    user_email = session.get("user_email")
    user_feedback = []

    if user_email:
        c.execute("SELECT name, message, rating, timestamp FROM feedback WHERE user_email=? ORDER BY id DESC", (user_email,))
        user_feedback = [{"name": row[0], "message": row[1], "rating": row[2], "timestamp": row[3]} for row in c.fetchall()]

    c.execute("SELECT name, message, rating, timestamp FROM feedback ORDER BY id DESC")
    all_feedback = [{"name": row[0], "message": row[1], "rating": row[2], "timestamp": row[3]} for row in c.fetchall()]

    c.execute("SELECT COUNT(*), AVG(rating) FROM feedback")
    stats = c.fetchone()
    total_count = stats[0]
    avg_rating = round(stats[1], 2) if stats[1] else 0

    conn.close()
    return render_template("feedback_history.html", user_feedback=user_feedback,
                           all_feedback=all_feedback, total_count=total_count, avg_rating=avg_rating)

@app.route("/api/history")
def api_history():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()

    if "user_email" in session:
        user_email = session["user_email"]
        c.execute("SELECT disease FROM history WHERE user_email=?", (user_email,))
        user_diseases = [row[0] for row in c.fetchall()]
        user_counter = Counter(user_diseases)
        user_data = [{"disease": name, "count": count} for name, count in user_counter.items()]
    else:
        user_data = []

    c.execute("SELECT disease FROM history")
    all_diseases = [row[0] for row in c.fetchall()]
    total_counter = Counter(all_diseases)
    total_data = [{"disease": name, "count": count} for name, count in total_counter.items()]

    conn.close()
    return jsonify({"total": total_data, "user": user_data})

@app.route("/api/feedback-ratings")
def feedback_ratings():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
    rows = c.fetchall()
    conn.close()

    return jsonify({str(rating): count for rating, count in rows})

if __name__ == "__main__":
    app.run(debug=True)
