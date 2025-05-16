from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


def call_llm(messages):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))

    response = client.chat.completions.create(
        model="deepseek-chat", messages=messages, temperature=0.7
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    # Test the LLM call
    messages = [
        {
            "role": "user",
            "content": "In a few words, what's the meaning of life? (Speaking in Chinese)",
        }
    ]
    response = call_llm(messages)
    print(f"Prompt: {messages[0]['content']}")
    print(f"Response: {response}")
