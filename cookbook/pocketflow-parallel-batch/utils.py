import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio

load_dotenv()


async def call_llm(prompt):
    client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))
    r = await client.chat.completions.create(
        model="deepseek-chat", messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content


if __name__ == "__main__":

    async def run_test():
        print("## Testing async call_llm with Anthropic")
        prompt = "In a few words, what is the meaning of life?"
        print(f"## Prompt: {prompt}")
        response = await call_llm(prompt)
        print(f"## Response: {response}")

    asyncio.run(run_test())
