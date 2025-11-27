import google.generativeai as genai
import os
from pathlib import Path

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash")

# Test with one paper
paper_path = Path("input/accepted_paper_1.txt")
with open(paper_path, 'r') as f:
    content = f.read()

try:
    response = model.generate_content(f"Summarize this paper:\n\n{content}")
    print(response.text)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")