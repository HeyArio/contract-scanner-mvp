import os
import requests
from dotenv import load_dotenv

# 1. FORCE RELOAD .ENV
# This ignores the old cached key and forces Python to read the file again.
load_dotenv(override=True)

def test_gemini_connection():
    # Retrieve the key from .env
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not found in .env file.")
        return

    # 2. DEFINE THE URL (Using the standard working model first)
    # Note: 'gemini-2.5' does not exist yet. Using 'gemini-1.5-flash' to guarantee a connection.
    # If you have special access to a beta, change the model name below.
    model_name = "gemini-1.5-flash"
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    
    # Construct the full URL string
    raw_url = f"{base_url}?key={api_key}"

    # 3. THE MAGIC FIX (Sanitization)
    # This removes accidental quotes (" or '), spaces, and newlines that cause the "Adapter" error.
    clean_url = raw_url.strip().replace('"', '').replace("'", "")

    # Debugging print to PROVE we are using the new key
    print(f"DEBUG: Key being used ends in: ...{api_key[-5:]}")
    print(f"DEBUG: URL is clean: '{clean_url}'")

    # Define headers and payload
    headers = {
        'Content-Type': 'application/json'
    }
    
    payload = {
        "contents": [{
            "parts": [{"text": "Hello, simply reply with 'Connection Successful'."}]
        }]
    }

    try:
        # 4. SEND THE REQUEST
        response = requests.post(clean_url, headers=headers, json=payload)
        
        # Check results
        if response.status_code == 200:
            print("\n✅ SUCCESS!")
            print("Response:", response.json()['candidates'][0]['content']['parts'][0]['text'])
        else:
            print(f"\n⚠️ Connection worked, but API returned error {response.status_code}:")
            print(response.text)

    except requests.exceptions.MissingSchema as e:
        print(f"\n❌ CRITICAL URL ERROR: {e}")
        print("This usually means the URL still has hidden quotes.")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    test_gemini_connection()