from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()


def stream_llm(prompt):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "your-api-key"))

    # Make a streaming chat completion request
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        stream=True,  # Enable streaming
    )
    return response


if __name__ == "__main__":
    print("## Testing streaming LLM")
    prompt = "你好"
    print(f"## Prompt: {prompt}")
    # response = fake_stream_llm(prompt)
    response = stream_llm(prompt)
    print(f"## Response: ")
    for chunk in response:
        if (
            hasattr(chunk.choices[0].delta, "content")
            and chunk.choices[0].delta.content is not None
        ):
            chunk_content = chunk.choices[0].delta.content
            # Print the incoming text without a newline (simulate real-time streaming)
            print(chunk_content, end="", flush=True)
