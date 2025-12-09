import streamlit as st
import requests  # <--- NEW: Using direct HTTP requests
import pypdf
import os
import json
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()

st.set_page_config(
    page_title="Hoghoughi AI - Contract Scanner",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Get API Key
# 1. Get API Key
# We use .strip() to remove accidental spaces or newlines from the .env file
api_key = os.environ.get("GOOGLE_API_KEY", "").strip() 

if not api_key:
    try:
        api_key = st.secrets["GOOGLE_API_KEY"].strip()
    except:
        st.error("⚠️ خطای امنیتی: کلید API پیدا نشد.")
        st.stop()
# --- THE LEGAL BRAIN (System Prompt) ---
SYSTEM_PROMPT = """
You are a Senior Legal Advisor specialized in the Civil Law of Iran (Qanun-e Madani).
Your task is to analyze the provided contract text (in Farsi) and identify risks based on Iranian law.

CRITICAL RULES:
1.  **Output Format:** Return ONLY a valid JSON object. Do not add markdown like ```json`.
2.  **Language:** All explanations must be in simple, clear Farsi (Persian).
3.  **Risk Calibration:**
    * **High Risk (Red):** Unilateral termination (فسخ یک‌طرفه), Waiver of all options (اسقاط کافه خیارات), Uncapped penalties (جریمه بدون سقف), undefined arbitration (داوری مبهم).
    * **Medium Risk (Yellow):** Vague timelines, automatic renewal without notice.

JSON STRUCTURE:
{
  "summary": "A 2-sentence simple story of what this contract is about in Farsi",
  "contract_type": "Type of contract (e.g., Ejareh, Peymankari)",
  "risk_score": Integer between 0-100 (100 is safe),
  "parties": ["Name 1", "Name 2"],
  "duration": "Duration of contract",
  "critical_alerts": [
    {
      "clause_text": "The exact Farsi text from the contract",
      "risk_explanation": "Why this is dangerous in simple Farsi",
      "severity": "HIGH" or "MEDIUM",
      "legal_term": "The legal jargon used (e.g., Esghat-e Kaff-e Khiarat)",
      "suggestion": "What to ask for instead"
    }
  ],
  "missing_clauses": ["List of important clauses that are missing"]
}
"""

# --- HELPER FUNCTIONS ---
def extract_text(uploaded_file):
    """Smart function to handle both PDF and Text files"""
    try:
        if uploaded_file.name.endswith('.pdf'):
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif uploaded_file.name.endswith('.txt'):
            return str(uploaded_file.read(), "utf-8")
        else:
            return "فرمت فایل پشتیبانی نمی‌شود."
    except Exception as e:
        return f"Error reading file: {e}"

def analyze_contract(text):
    """
    UPDATED: Uses direct REST API call to Gemini 2.5 Flash
    This bypasses the SDK and hits the URL directly.
    """
    # The exact URL you requested
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=){api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construct the payload
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{SYSTEM_PROMPT}\n\nCONTRACT TEXT:\n{text}"
            }]
        }],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }

    try:
        # Make the request
        response = requests.post(url, headers=headers, json=payload)
        
        # Check for HTTP errors (404, 500, etc.)
        if response.status_code != 200:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return None

        # Parse the JSON response
        result = response.json()
        
        # Extract the text from the candidates
        raw_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Clean up code fences if the model added them despite instructions
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_json)

    except Exception as e:
        st.error(f"Analysis Failed: {e}")
        return None

# --- UI LAYOUT ---
st.title("🇮🇷 دستیار هوشمند بررسی قرارداد (MVP)")
st.markdown("""
این سیستم با استفاده از **Gemini 2.5 Flash** قرارداد شما را بررسی می‌کند.
فایل PDF یا متن قرارداد را آپلود کنید.
""")

uploaded_file = st.file_uploader("آپلود فایل قرارداد", type=["pdf", "txt"])

if uploaded_file:
    with st.spinner("⏳ در حال استخراج متن و آنالیز با مدل جدید..."):
        # 1. Extract Text
        contract_text = extract_text(uploaded_file)
        
        # 2. Analyze
        if len(contract_text) < 10:
            st.warning("متن کافی استخراج نشد.")
        else:
            analysis = analyze_contract(contract_text)
            
            if analysis:
                st.divider()
                # Report Dashboard
                col1, col2, col3 = st.columns(3)
                with col1:
                    score = analysis.get('risk_score', 0)
                    color = "green" if score >= 80 else "orange" if score >= 50 else "red"
                    st.markdown(f"### امتیاز ریسک: :{color}[{score}/100]")
                with col2:
                    st.markdown(f"**نوع:** {analysis.get('contract_type', 'نامشخص')}")
                with col3:
                    st.markdown(f"**مدت:** {analysis.get('duration', 'نامشخص')}")

                st.info(f"💡 **خلاصه:** {analysis.get('summary')}")

                st.subheader("🚩 ریسک‌های شناسایی شده")
                alerts = analysis.get('critical_alerts', [])
                if not alerts:
                    st.success("ریسک بزرگی پیدا نشد.")
                
                for alert in alerts:
                    icon = "⛔" if alert.get('severity') == "HIGH" else "⚠️"
                    with st.expander(f"{icon} {alert.get('risk_explanation')[:60]}...", expanded=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**بند:** `{alert.get('clause_text')}`")
                            st.markdown(f"**تحلیل:** {alert.get('risk_explanation')}")
                        with c2:
                            st.markdown(f"**اصطلاح:** `{alert.get('legal_term')}`")
                            st.markdown(f"💡 **پیشنهاد:** {alert.get('suggestion')}")

                if analysis.get('missing_clauses'):
                    st.warning(f"**بندهای جامانده:** {', '.join(analysis['missing_clauses'])}")

                with st.expander("مشاهده متن خام"):
                    st.text(contract_text)