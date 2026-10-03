import io
import json
import os
import re
from typing import Any, Dict, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from .env if present
load_dotenv()

from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

# Optional imports with graceful degradation
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from twilio.rest import Client as TwilioClient
    HAS_TWILIO = True
except ImportError:
    HAS_TWILIO = False


# Page Configuration
st.set_page_config(
    page_title="MacroSnap - AI Nutrition & Calorie Tracker",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Metric pill styling */
    .macro-badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .macro-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        color: #10b981;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .macro-pill.calories {
        background: rgba(245, 158, 11, 0.12);
        border-color: rgba(245, 158, 11, 0.35);
        color: #f59e0b;
    }
    .macro-pill.protein {
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
        color: #ef4444;
    }
    .macro-pill.carbs {
        background: rgba(59, 130, 246, 0.12);
        border-color: rgba(59, 130, 246, 0.35);
        color: #3b82f6;
    }
    .macro-pill.fat {
        background: rgba(168, 85, 247, 0.12);
        border-color: rgba(168, 85, 247, 0.35);
        color: #a855f7;
    }
    .stProgress > div > div > div > div {
        background-color: #10B981;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_config_val(key: str, default: str = "") -> str:
    """Safely fetch config from st.secrets, os.environ, or st.session_state."""
    # 1. Streamlit secrets
    try:
        if key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass

    # 2. Environment variable
    env_val = os.getenv(key)
    if env_val:
        return env_val.strip()

    # 3. Session state fallback
    return str(st.session_state.get(key, default)).strip()


# Configuration resolution
gemini_key = get_config_val("GEMINI_API_KEY")
model_name = get_config_val("GEMINI_MODEL", "gemini-2.5-flash")
twilio_sid = get_config_val("TWILIO_ACCOUNT_SID")
twilio_token = get_config_val("TWILIO_AUTH_TOKEN")
twilio_from = get_config_val("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
twilio_content_sid = get_config_val("TWILIO_CONTENT_SID")


def init_session():
    """Initialize all session state parameters."""
    if "onboarded" not in st.session_state:
        st.session_state.onboarded = False
    if "name" not in st.session_state:
        st.session_state.name = ""
    if "whatsapp_number" not in st.session_state:
        st.session_state.whatsapp_number = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "daily_targets" not in st.session_state:
        st.session_state.daily_targets = {
            "calories": 2000,
            "protein": 130,
            "carbs": 220,
            "fat": 65,
        }
    if "daily_totals" not in st.session_state:
        st.session_state.daily_totals = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
        }
    if "chat" not in st.session_state:
        st.session_state.chat = None
    if "api_key" not in st.session_state:
        st.session_state.api_key = gemini_key


init_session()


@st.cache_resource
def get_gemini_client(api_key: str):
    if not HAS_GENAI:
        return None
    return genai.Client(api_key=api_key)


def get_twilio_client():
    if not HAS_TWILIO:
        return None
    sid = get_config_val("TWILIO_ACCOUNT_SID")
    token = get_config_val("TWILIO_AUTH_TOKEN")
    if sid and token:
        try:
            return TwilioClient(sid, token)
        except Exception:
            return None
    return None


def extract_macros(text: str) -> Tuple[str, Optional[Dict[str, int]]]:
    """Parse out structured macro tag if present, returning cleaned text and macro dict."""
    pattern = r"\[MACROS:\s*calories=(\d+),\s*protein=(\d+),\s*carbs=(\d+),\s*fat=(\d+)\]"
    match = re.search(pattern, text)
    if match:
        cal = int(match.group(1))
        p = int(match.group(2))
        c = int(match.group(3))
        f = int(match.group(4))
        cleaned = re.sub(pattern, "", text).strip()
        return cleaned, {"calories": cal, "protein": p, "carbs": c, "fat": f}
    return text, None


def render_message(message: Dict[str, Any]):
    """Render a single chat message with formatting and optional macro tags."""
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.markdown(message["content"])
            if message.get("macros"):
                m = message["macros"]
                st.markdown(
                    f"""
                    <div class="macro-badge-container">
                        <span class="macro-pill calories">🔥 {m['calories']} kcal</span>
                        <span class="macro-pill protein">🥩 {m['protein']}g Protein</span>
                        <span class="macro-pill carbs">🍞 {m['carbs']}g Carbs</span>
                        <span class="macro-pill fat">🥑 {m['fat']}g Fat</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        elif message["kind"] == "image":
            st.image(message["content"], caption="Logged Meal Photo", use_container_width=True)


def add_message(role: str, kind: str, content: Any, macros: Optional[Dict[str, int]] = None):
    st.session_state.messages.append(
        {"role": role, "kind": kind, "content": content, "macros": macros}
    )
    render_message(st.session_state.messages[-1])


def ask_gemini(parts) -> str:
    """Send parts (text or images) to Gemini chat."""
    if not st.session_state.chat:
        return "Gemini chat session is not initialized. Please verify your API key."
    try:
        response = st.session_state.chat.send_message(parts)
        return response.text
    except Exception as error:
        return f"⚠️ Unable to process meal: {error}"


def clean_whatsapp_text(text: str) -> str:
    if not text:
        return "No nutrition summary available for today."
    text = text.strip()
    return text[:1500] + "..." if len(text) > 1500 else text


def send_whatsapp(to_number: str, user_name: str, summary: str) -> Tuple[bool, str]:
    """Send daily summary via Twilio WhatsApp API."""
    twilio_client = get_twilio_client()
    if not twilio_client:
        return False, "Twilio client is not configured. Please check your Account SID and Auth Token."

    from_number = get_config_val("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    content_sid = get_config_val("TWILIO_CONTENT_SID")

    # Ensure to_number has whatsapp: prefix
    to_whatsapp = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

    try:
        if content_sid:
            content_variables = json.dumps(
                {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
            )
            msg = twilio_client.messages.create(
                from_=from_number,
                to=to_whatsapp,
                content_sid=content_sid,
                content_variables=content_variables,
            )
        else:
            # Fallback to direct text body if no Content Template SID is specified
            body_msg = f"🥗 *MacroSnap Daily Summary for {user_name}*\n\n{clean_whatsapp_text(summary)}"
            msg = twilio_client.messages.create(
                from_=from_number,
                to=to_whatsapp,
                body=body_msg,
            )
        return True, msg.sid
    except Exception as error:
        return False, str(error)


# -------------------------------------------------------------
# Configuration Guard: Check API Key
# -------------------------------------------------------------
active_api_key = st.session_state.api_key or gemini_key

if not active_api_key:
    st.title("🥗 MacroSnap")
    st.subheader("Welcome! Let's get your AI Nutrition Assistant ready.")
    st.info(
        "MacroSnap uses Google Gemini to instantly estimate calories and macronutrients from food photos and text."
    )

    with st.container(border=True):
        st.write("### 🔑 Setup Your Gemini API Key")
        entered_key = st.text_input(
            "Enter Gemini API Key",
            type="password",
            placeholder="AIzaSy...",
            help="Get your free API key at https://aistudio.google.com/",
        )
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("Save & Continue", type="primary", use_container_width=True):
                if entered_key.strip():
                    st.session_state.api_key = entered_key.strip()
                    st.rerun()
                else:
                    st.warning("Please provide a valid API key.")
        with col2:
            st.caption(
                "💡 **Tip:** You can permanently configure this by adding `GEMINI_API_KEY=\"your_key\"` to `.streamlit/secrets.toml` or `.env`."
            )
    st.stop()


# -------------------------------------------------------------
# Onboarding Flow
# -------------------------------------------------------------
if not st.session_state.onboarded:
    st.title("🥗 MacroSnap")
    st.caption("Snap it. Track it. Reach your nutrition goals with AI.")

    with st.form("onboarding_form", border=True):
        st.write("### Personalize Your Tracker")
        name = st.text_input("What's your name?", placeholder="e.g. Alex", value=st.session_state.name)

        col_a, col_b = st.columns(2)
        with col_a:
            whatsapp_number = st.text_input(
                "WhatsApp Number (with country code)",
                placeholder="+919876543210",
                value=st.session_state.whatsapp_number,
                help="MacroSnap will send your daily nutrition recaps to this number.",
            )
        with col_b:
            goal_preset = st.selectbox(
                "Daily Goal Preset",
                [
                    "Balanced Maintenance (2,000 kcal)",
                    "Fat Loss / Calorie Deficit (1,600 kcal)",
                    "Muscle Gain / High Protein (2,400 kcal)",
                    "Custom",
                ],
            )

        if goal_preset == "Custom":
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                target_cal = st.number_input("Target Calories", 1000, 5000, 2000, step=50)
            with c2:
                target_p = st.number_input("Target Protein (g)", 30, 300, 130, step=5)
            with c3:
                target_c = st.number_input("Target Carbs (g)", 30, 600, 220, step=10)
            with c4:
                target_f = st.number_input("Target Fat (g)", 10, 200, 65, step=5)
        elif "Fat Loss" in goal_preset:
            target_cal, target_p, target_c, target_f = 1600, 140, 140, 50
        elif "Muscle Gain" in goal_preset:
            target_cal, target_p, target_c, target_f = 2400, 175, 260, 75
        else:
            target_cal, target_p, target_c, target_f = 2000, 130, 220, 65

        submitted = st.form_submit_button("Start Tracking 🚀", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.warning("Please enter your name to continue.")
        else:
            st.session_state.name = name.strip()
            st.session_state.whatsapp_number = whatsapp_number.strip()
            st.session_state.daily_targets = {
                "calories": target_cal,
                "protein": target_p,
                "carbs": target_c,
                "fat": target_f,
            }

            # Initialize Gemini chat session
            try:
                client = get_gemini_client(active_api_key)
                st.session_state.chat = client.chats.create(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.4,
                    ),
                )
                st.session_state.messages = []
                st.session_state.onboarded = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to connect to Gemini API: {e}. Please check your API key.")
    st.stop()


# -------------------------------------------------------------
# Active Tracker & Chat Interface
# -------------------------------------------------------------

# Ensure chat session is ready
if st.session_state.chat is None:
    try:
        client = get_gemini_client(active_api_key)
        st.session_state.chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.4,
            ),
        )
    except Exception as e:
        st.error(f"Error starting chat session: {e}")


# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🥗 **MacroSnap**")
    st.caption(f"Tracking for **{st.session_state.name}**")
    if st.session_state.whatsapp_number:
        st.caption(f"📲 WhatsApp: `{st.session_state.whatsapp_number}`")

    st.markdown("---")
    st.markdown("#### 📊 **Daily Nutrition Progress**")

    # Metrics
    tot = st.session_state.daily_totals
    tar = st.session_state.daily_targets

    # Calories Progress
    cal_pct = min(1.0, tot["calories"] / max(1, tar["calories"]))
    st.write(f"**Calories:** {tot['calories']} / {tar['calories']} kcal")
    st.progress(cal_pct)

    # Protein Progress
    p_pct = min(1.0, tot["protein"] / max(1, tar["protein"]))
    st.write(f"🥩 **Protein:** {tot['protein']}g / {tar['protein']}g")
    st.progress(p_pct)

    # Carbs Progress
    c_pct = min(1.0, tot["carbs"] / max(1, tar["carbs"]))
    st.write(f"🍞 **Carbs:** {tot['carbs']}g / {tar['carbs']}g")
    st.progress(c_pct)

    # Fat Progress
    f_pct = min(1.0, tot["fat"] / max(1, tar["fat"]))
    st.write(f"🥑 **Fat:** {tot['fat']}g / {tar['fat']}g")
    st.progress(f_pct)

    st.markdown("---")
    st.markdown("#### ⚡ **Quick Log Presets**")
    st.caption("Click to test or log common meals quickly:")
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        if st.button("🍳 Breakfast", use_container_width=True):
            st.session_state["preset_input"] = "2 scrambled eggs with 2 slices of whole wheat toast and black coffee"
    with col_q2:
        if st.button("🥗 Lunch Bowl", use_container_width=True):
            st.session_state["preset_input"] = "Grilled chicken salad with mixed greens, avocado, cherry tomatoes and olive oil"
    col_q3, col_q4 = st.columns(2)
    with col_q3:
        if st.button("🍎 Snack", use_container_width=True):
            st.session_state["preset_input"] = "1 medium apple with 2 tablespoons of peanut butter"
    with col_q4:
        if st.button("🥩 Dinner", use_container_width=True):
            st.session_state["preset_input"] = "Salmon fillet (200g) with steamed broccoli and 1 cup brown rice"

    st.markdown("---")
    with st.expander("⚙️ **Settings & Integrations**"):
        st.write(f"**Active Model:** `{model_name}`")
        twilio_ready = bool(get_twilio_client())
        if twilio_ready:
            st.success("🟢 Twilio WhatsApp Connected")
        else:
            st.info("ℹ️ Twilio is optional. You can still preview and copy summaries anytime.")

        if st.button("🔄 Reset Daily Tracker", use_container_width=True):
            st.session_state.daily_totals = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
            st.session_state.messages = []
            client = get_gemini_client(active_api_key)
            st.session_state.chat = client.chats.create(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                ),
            )
            st.rerun()


# ==================== MAIN CHAT HEADER ====================
head_col, act_col1, act_col2 = st.columns([4, 2, 2], vertical_alignment="center")

with head_col:
    st.title("🥗 MacroSnap")
    st.caption("AI Meal Analysis • Instant Macros • Daily Recaps")

with act_col1:
    summary_disabled = len(st.session_state.messages) <= 1
    if st.button("📋 Daily Summary", disabled=summary_disabled, use_container_width=True):
        with st.spinner("Generating daily summary..."):
            summary_text = ask_gemini([SUMMARY_REQUEST_PROMPT])
            st.session_state["current_summary"] = summary_text

with act_col2:
    if st.button("📲 Send WhatsApp", disabled=summary_disabled, use_container_width=True):
        if not st.session_state.whatsapp_number:
            st.warning("Please configure your WhatsApp number in the sidebar or onboarding first.")
        else:
            with st.spinner("Summarizing & dispatching via WhatsApp..."):
                summary_text = ask_gemini([SUMMARY_REQUEST_PROMPT])
                success, info = send_whatsapp(
                    st.session_state.whatsapp_number, st.session_state.name, summary_text
                )
                if success:
                    st.success("Sent! Check your WhatsApp 📲")
                else:
                    st.session_state["current_summary"] = summary_text
                    st.info(f"WhatsApp API notice: {info}. You can copy the summary below:")

# Display summary modal/expander if triggered
if "current_summary" in st.session_state and st.session_state["current_summary"]:
    with st.expander("📝 **Today's Nutrition Summary (Ready for WhatsApp)**", expanded=True):
        st.text_area("Summary", st.session_state["current_summary"], height=160)
        col_c1, col_c2 = st.columns([1, 3])
        with col_c1:
            if st.button("Close Summary"):
                st.session_state["current_summary"] = None
                st.rerun()

st.markdown("---")

# Render initial greeting or full message history
if not st.session_state.messages:
    add_message(
        "assistant",
        "text",
        WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name),
    )
else:
    for msg in st.session_state.messages:
        render_message(msg)

# Check preset input from quick buttons
preset_text = st.session_state.pop("preset_input", None)

# Chat Input supporting text and file attachment
user_input = st.chat_input(
    "Describe your meal, or attach a photo...",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp"],
)

# Handle either chat input or preset click
if user_input or preset_text:
    photo = None
    text = ""

    if user_input:
        if hasattr(user_input, "files") and user_input.files:
            photo = user_input.files[0]
        if hasattr(user_input, "text"):
            text = user_input.text
        elif isinstance(user_input, str):
            text = user_input
    elif preset_text:
        text = preset_text

    parts = []

    if photo is not None:
        photo_bytes = photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))

    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Estimate the portion size, calories, and macros.")

    if parts:
        with st.spinner("Analyzing meal & calculating macros..."):
            raw_answer = ask_gemini(parts)
            clean_answer, macros = extract_macros(raw_answer)

            # Update daily totals if macros were parsed
            if macros:
                st.session_state.daily_totals["calories"] += macros["calories"]
                st.session_state.daily_totals["protein"] += macros["protein"]
                st.session_state.daily_totals["carbs"] += macros["carbs"]
                st.session_state.daily_totals["fat"] += macros["fat"]

            add_message("assistant", "text", clean_answer, macros=macros)
            st.rerun()
