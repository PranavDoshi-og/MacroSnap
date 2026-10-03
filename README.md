# 🥗 MacroSnap — AI Nutrition & Calorie Tracker

MacroSnap is a modern AI-powered nutrition buddy built with **Streamlit** and **Google Gemini (2.5 Flash)**. It allows users to snap or upload meal photos, describe what they ate in plain English, get instant calorie and macronutrient breakdowns, and text daily nutrition summaries straight to WhatsApp via **Twilio**.

---

## ✨ Key Features

- **📸 Multimodal Food Recognition:** Upload or snap photos of your plates, snacks, or grocery labels. Powered by Gemini's vision capabilities.
- **💬 Natural Language Meal Logging:** Simply type what you ate (e.g., *"2 scrambled eggs, avocado toast, and an iced latte"*).
- **📊 Real-time Macro Dashboard:** Live sidebar tracking your daily intake vs. targets:
  - 🔥 Calories (kcal)
  - 🥩 Protein (g)
  - 🍞 Carbohydrates (g)
  - 🥑 Fats (g)
- **⚡ Quick-Log Presets:** Instant one-click presets for common breakfasts, lunch bowls, snacks, and dinners.
- **📲 WhatsApp Integration:**
  - One-click daily recap formatted specifically for WhatsApp.
  - Direct delivery to your phone via Twilio WhatsApp API.
  - Built-in fallback to copy summaries directly if Twilio isn't set up.
- **🛡️ Resilient Configuration:**
  - Supports `.env` files, Streamlit secrets (`.streamlit/secrets.toml`), environment variables, or in-app API key input.
  - Doesn't crash on missing optional credentials.

---

## 📁 Project Structure

```
AI-Chatbox/
├── app.py                     # Main Streamlit application & interactive UI
├── prompts.py                 # System instructions and prompt templates
├── requirements.txt           # Python dependencies
├── .env.example               # Template for environment variables
├── .gitignore                 # Standard Python & Streamlit ignore rules
├── README.md                  # Documentation and quickstart guide
└── .streamlit/
    ├── config.toml            # Custom emerald/slate theme configuration
    └── secrets.toml.example   # Example Streamlit secrets configuration
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12 / 3.14)
- A Google Gemini API Key ([Get one for free at Google AI Studio](https://aistudio.google.com/))
- (Optional) A Twilio account for WhatsApp messaging ([Twilio Console](https://console.twilio.com/))

### 2. Install Dependencies
In your terminal, navigate to the project directory and install the required packages:

```bash
pip install -r requirements.txt
```

### 3. Configure Secrets
Create a `.env` file in the root directory (or copy from `.env.example`):

```bash
# Windows PowerShell:
Copy-Item .env.example .env
```

Or edit `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-gemini-api-key-here"
GEMINI_MODEL = "gemini-2.5-flash"

# Optional: Twilio WhatsApp Setup
TWILIO_ACCOUNT_SID = "your-twilio-account-sid"
TWILIO_AUTH_TOKEN = "your-twilio-auth-token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
TWILIO_CONTENT_SID = ""
```

> **Note:** If you don't configure an API key in a file, you can also enter it securely directly in the app UI on launch!

### 4. Run the Application
Launch MacroSnap with Streamlit:

```bash
python -m streamlit run app.py
# or if streamlit is in your system PATH:
streamlit run app.py
```

Open your browser to `http://localhost:8501`.

---

## 📲 Optional: Setting Up Twilio WhatsApp

To send summaries straight to your WhatsApp number:

1. Go to the [Twilio Console](https://console.twilio.com/) and navigate to **Messaging > Try it out > Send a WhatsApp message**.
2. Follow the prompt to connect your personal WhatsApp number to the Twilio Sandbox (e.g. send `join <word>` to `+1 415 523 8886`).
3. Copy your **Account SID** and **Auth Token** into `.env` or `.streamlit/secrets.toml`.
4. In the app onboarding, enter your WhatsApp number in international format (e.g. `+91XXXXXXXXXX`).
5. Click **📲 Send WhatsApp** when your daily meals are logged!

*(If you don't want to set up Twilio, click **📋 Daily Summary** to view and copy your recap anytime!)*

---

## 🛠️ Tech Stack

- **Frontend & App Framework:** [Streamlit](https://streamlit.io/)
- **AI Engine:** [Google GenAI SDK](https://github.com/google-gemini/generative-ai-python) (`gemini-2.5-flash`)
- **Messaging:** [Twilio Python SDK](https://github.com/twilio/twilio-python)
- **Image Processing:** [Pillow (PIL)](https://python-pillow.org/)
- **Environment Management:** [python-dotenv](https://github.com/theskumar/python-dotenv)
