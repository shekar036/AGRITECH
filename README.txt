
# 🌿 AGRITECH (AI-Powered Plant Disease Detection System)

A web application built with Flask that detects plant diseases from uploaded leaf images using deep learning. It also provides disease insights through Gemini AI and allows users to track history and give feedback.

---

## ✨ Features

* 🔐 **Authentication**
  Users can sign up, log in, and log out securely. Sessions are managed using Flask's session handling.

* 🧠 **Disease Prediction (AI)**
  Uses the `google/efficientnet-b0` model to classify leaf diseases via Hugging Face's `transformers.pipeline`.

* 🤖 **Gemini AI Integration**
  Google Gemini 2.0 API is used to provide causes, cures, prevention, and recommendations for detected diseases.

* 🗃️ **Detection History**
  Stores each user's uploaded image, prediction result, and timestamp in an SQLite database for future reference.

* 💬 **Feedback System**
  Allows users (even guests) to submit feedback with a message and rating (1–5). Prevents spamming using a cooldown timer.

* 📊 **Data Analytics APIs**
  APIs return chart-ready JSON data for disease prediction frequency and feedback ratings (used in dashboard visualizations).

---

## 🛠️ Tech Stack & Usage

| Technology                   | Used For                                         |
| ---------------------------- | ------------------------------------------------ |
| 🐍 Python (Flask)            | Backend server, routing, session management      |
| 🧠 Hugging Face Transformers | Image classification using EfficientNet-B0 model |
| 🧬 Google Gemini AI          | Generating disease-related information           |
| 💾 SQLite                    | Storing users, history, and feedback             |
| 🖼️ PIL                      | Processing uploaded image files                  |
| 🌐 HTML + Jinja              | Frontend rendering using Flask templates         |
| 🔐 Session                   | Managing user state across routes                |

---

## 📂 Folder Structure

```
project/
├── app.py                  # Main application file
├── users.db                # SQLite database
├── templates/              # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── Agri_tech.html
│   ├── feedback.html
│   └── history.html
├── static/
│   └── uploads/            # Stores user-uploaded leaf images
```

---

## ⚙️ Setup Instructions

1. 📦 **Clone the repository**

   ```bash
   git clone https://github.com/your-username/plant-disease-detector.git
   cd plant-disease-detector
   ```

2. 🧪 **Create virtual environment and install dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 🔑 **Set Gemini API key**
   In `app.py`, update:

   ```python
   GEMINI_API_KEY = "your-google-api-key"
   ```

4. ▶️ **Run the app**

   ```bash
   python app.py
   ```

   Visit: `http://127.0.0.1:5000`

---

## 🔗 Key Routes

| Route                   | Description                      |
| ----------------------- | -------------------------------- |
| `/`                     | Home page                        |
| `/login`, `/signup`     | User login & registration        |
| `/detect`               | Disease detection interface      |
| `/predict`              | Image upload and AI inference    |
| `/feedback`             | Submit feedback with rating      |
| `/history`              | View past detections             |
| `/api/history`          | JSON API for disease frequency   |
| `/api/feedback-ratings` | JSON API for feedback statistics |

---

## 📌 Notes

* Make sure internet access is enabled for Gemini AI to respond.
* SQLite is used for simplicity. You can upgrade to PostgreSQL/MySQL for production.
* Disease predictions are based on image quality. Ensure clear, focused leaf images.
