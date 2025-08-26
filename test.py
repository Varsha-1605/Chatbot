import google.generativeai as genai
import os

# Option 1: Hardcode your API key (not recommended for production)
# Replace 'YOUR_API_KEY' with your actual key
API_KEY = "AIzaSyAEAkWAAgA6gS25cTzw_P4yfXO7KM1d2Dw"
genai.configure(api_key=API_KEY)

# Option 2: Load the API key from an environment variable (recommended)
# This mimics the behavior of your chatbot
# Be sure your .env file is configured correctly and the app is restarted
# from dotenv import load_dotenv
# load_dotenv()
# genai.configure(api_key=os.getenv('GEMINI_API_KEY'))


try:
    # Attempt to list the models available with your API key.
    # This is a good way to verify authentication without generating content.
    # The 'list_models' method is an effective way to confirm access.
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model found: {m.name}")
    
    # Or, send a simple content generation request
    # model = genai.GenerativeModel('gemini-pro')
    # model = genai.GenerativeModel('gemini-2.0-flash')
    model = genai.GenerativeModel('gemini-1.5-flash')

    response = model.generate_content("Hello, can you help me?")
    
    print("\n--- API Key is working! ---")
    print(f"Bot response: {response.text}")

except Exception as e:
    print("\n--- API Key is NOT working. ---")
    print(f"Error: {e}")
    print("\nPossible reasons for failure:")
    print("1. The API key is invalid or incomplete.")
    print("2. The API key has been restricted or has run out of requests.")
    print("3. There is a network or firewall issue.")