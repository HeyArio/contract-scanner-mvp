import streamlit as st
import google.generativeai as genai
import pypdf
import os
import json
from dotenv import load_dotenv

# --- CONFIGURATION ---
# 1. Load environment variables from .env file (if running locally)
load_dotenv()

st.set_page_config(
    page_title="Hoghoughi AI - Contract Scanner",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Setup API Key (Works for both Local .env and Render Cloud Env)
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    # Fallback to Streamlit secrets if needed
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except:
        st.error("⚠️ خطای امنیتی: کلید API پیدا نشد. لطفا فایل .env را بررسی کنید.")
        st.stop()

genai.configure(api_key=api_key)

# --- THE BRAIN (System Prompt) ---
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
  "missing_clauses": ["List of important clauses that are missing (e.g., Force Majeure, Confidentiality)"]
}
"""

# --- HELPER FUNCTIONS ---
def extract_text(uploaded_file):
    """Smart function to handle both PDF and Text files"""
    try:
        # Case 1: PDF
        if uploaded_file.name.endswith('.pdf'):
            reader = pypdf.PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
            
        # Case 2: TXT
        elif uploaded_file.name.endswith('.txt'):
            # Text files are bytes, need to decode
            return str(uploaded_file.read(), "utf-8")
            
        else:
            return "فرمت فایل پشتیبانی نمی‌شود."
            
    except Exception as e:
        return f"Error reading file: {e}"

def analyze_contract(text):
    """Sends text to Gemini and parses the JSON response"""
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, f"CONTRACT TEXT:\n{text}"],
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI Analysis Failed: {e}")
        return None

# --- UI LAYOUT ---
st.title("🇮🇷 دستیار هوشمند بررسی قرارداد (MVP)")
st.markdown("""
این سیستم با استفاده از هوش مصنوعی، قرارداد شما را بر اساس **قوانین مدنی ایران** بررسی می‌کند.
فایل PDF یا متن قرارداد را آپلود کنید تا ریسک‌های پنهان آن مشخص شود.
""")

# UPDATED: Allows both 'pdf' and 'txt'
uploaded_file = st.file_uploader("آپلود فایل قرارداد", type=["pdf", "txt"])

if uploaded_file:
    with st.spinner("⏳ در حال استخراج متن و آنالیز حقوقی... (ممکن است ۳۰ ثانیه طول بکشد)"):
        # 1. Extract Text
        contract_text = extract_text(uploaded_file)
        
        # 2. Analyze with Gemini
        # Simple check to make sure we actually got text
        if len(contract_text) < 10:
            st.warning("متن کافی از فایل استخراج نشد. اگر PDF اسکن شده است، فعلا پشتیبانی نمی‌شود.")
        else:
            analysis = analyze_contract(contract_text)
            
            if analysis:
                # --- REPORT DASHBOARD ---
                st.divider()
                
                # Header Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    score = analysis.get('risk_score', 0)
                    color = "green" if score >= 80 else "orange" if score >= 50 else "red"
                    st.markdown(f"### امتیاز ریسک: :{color}[{score}/100]")
                with col2:
                    st.markdown(f"**نوع قرارداد:** {analysis.get('contract_type', 'نامشخص')}")
                with col3:
                    st.markdown(f"**مدت:** {analysis.get('duration', 'نامشخص')}")

                # Simple Summary
                st.info(f"💡 **خلاصه ساده:** {analysis.get('summary')}")

                # Risk Breakdown
                st.subheader("🚩 هشدارهای قرمز (بندهای خطرناک)")
                
                alerts = analysis.get('critical_alerts', [])
                if not alerts:
                    st.success("هیچ ریسک بزرگی پیدا نشد! (باز هم با وکیل مشورت کنید)")
                
                for alert in alerts:
                    # Use a red box for high risk, yellow for medium
                    icon = "⛔" if alert.get('severity') == "HIGH" else "⚠️"
                    with st.expander(f"{icon} {alert.get('risk_explanation')[:60]}...", expanded=True):
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**متن قرارداد:** `{alert.get('clause_text')}`")
                            st.markdown(f"**تحلیل:** {alert.get('risk_explanation')}")
                        with c2:
                            st.markdown(f"**اصطلاح حقوقی:** `{alert.get('legal_term')}`")
                            st.markdown(f"💡 **پیشنهاد:** {alert.get('suggestion')}")

                # Missing Clauses
                if analysis.get('missing_clauses'):
                    st.warning(f"**جای این بندها خالی است:** {', '.join(analysis['missing_clauses'])}")

                # Raw Text Viewer
                with st.expander("مشاهده متن خام استخراج شده"):
                    st.text(contract_text)

# Disclaimer footer
st.markdown("---")
st.caption("⚠️ سلب مسئولیت: این ابزار جایگزین وکیل نیست. هوش مصنوعی ممکن است خطا داشته باشد.")