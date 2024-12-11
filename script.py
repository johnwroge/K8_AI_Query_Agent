import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    print("Success! API key is working")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")