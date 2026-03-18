import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

models = genai.list_models()
for m in models:
    # show only models that support generateContent
    if "generateContent" in m.supported_generation_methods:
        print(m.name)