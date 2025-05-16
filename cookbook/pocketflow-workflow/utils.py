import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def call_llm(prompt):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Speak Chinese.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    return r.choices[0].message.content


# Example usage
if __name__ == "__main__":
    print(call_llm("给我讲一个玩笑"))
