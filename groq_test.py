import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

input_string = "你好ㄚ可愛的模型"
model_name = "gpt-4o-mini"

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "你好ㄚ可愛的模型",
        }
    ],
    model="llama3-8b-8192",
)

print(chat_completion.choices[0].message.content)