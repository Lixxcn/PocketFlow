import asyncio
from pocketflow import AsyncNode, AsyncFlow
from utils import call_llm


class AsyncHinter(AsyncNode):
    async def prep_async(self, shared):
        # Wait for message from guesser (or empty string at start)
        guess = await shared["hinter_queue"].get()
        if guess == "GAME_OVER":
            return None
        return (
            shared["target_word"],
            shared["forbidden_words"],
            shared.get("past_guesses", []),
            shared.get("past_hints", []),  # Add past hints to inputs
        )

    async def exec_async(self, inputs):
        if inputs is None:
            return None
        target, forbidden, past_guesses, past_hints = inputs  # Receive past hints
        prompt = f"为成语 '{target}' 生成提示。\n禁用词汇: {forbidden}"
        if past_guesses:
            prompt += f"\n之前的错误猜测: {past_guesses}\n请提供更具体的提示。"
        if past_hints:  # Add instruction about past hints
            prompt += f"\n之前给出的提示: {past_hints}\n请勿重复使用这些提示。"
        prompt += "\n提示词最多使用20个字。"

        hint = call_llm(prompt)
        print(f"\n提示者给出的提示是 - {hint}")
        return hint

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res is None:
            return "end"
        # Add the generated hint to the list of past hints
        if "past_hints" not in shared:
            shared["past_hints"] = []
        shared["past_hints"].append(exec_res)

        # Send hint to guesser
        await shared["guesser_queue"].put(exec_res)
        return "continue"


class AsyncGuesser(AsyncNode):
    async def prep_async(self, shared):
        # Wait for hint from hinter
        hint = await shared["guesser_queue"].get()
        return hint, shared.get("past_guesses", [])

    async def exec_async(self, inputs):
        hint, past_guesses = inputs
        prompt = f"根据提示: {hint}, 之前的错误猜测: {past_guesses}, 请进行新的猜测。直接回复一个中文成语:"
        guess = call_llm(prompt)
        print(f"猜词者猜测是 - {guess}")
        return guess

    async def post_async(self, shared, prep_res, exec_res):
        # Check if guess is correct
        if exec_res.lower() == shared["target_word"].lower():
            print("Game Over - Correct guess!")
            await shared["hinter_queue"].put("GAME_OVER")
            return "end"

        # Store the guess in shared state
        if "past_guesses" not in shared:
            shared["past_guesses"] = []
        shared["past_guesses"].append(exec_res)

        # Send guess to hinter
        await shared["hinter_queue"].put(exec_res)
        return "continue"


async def main():
    print("=========== 成语猜词游戏 ===========")

    # 获取用户输入的成语
    target_idiom = input("请输入您想让AI猜测的成语: ")

    # 根据成语生成禁用词汇 (成语的每个字)
    forbidden_chars = list(target_idiom)

    # Set up game
    shared = {
        "target_word": target_idiom,
        "forbidden_words": forbidden_chars,
        "hinter_queue": asyncio.Queue(),
        "guesser_queue": asyncio.Queue(),
        "past_hints": [],  # Initialize list for past hints
    }

    print(f"目标成语: {shared['target_word']}")
    print(f"禁用词汇: {shared['forbidden_words']}")
    print("============================================")

    # Initialize by sending empty guess to hinter
    await shared["hinter_queue"].put("")

    # Create nodes and flows
    hinter = AsyncHinter()
    guesser = AsyncGuesser()

    # Set up flows
    hinter_flow = AsyncFlow(start=hinter)
    guesser_flow = AsyncFlow(start=guesser)

    # Connect nodes to themselves for looping
    hinter - "continue" >> hinter
    guesser - "continue" >> guesser

    # Run both agents concurrently
    await asyncio.gather(hinter_flow.run_async(shared), guesser_flow.run_async(shared))

    print("=========== 游戏结束！ ===========")


if __name__ == "__main__":
    asyncio.run(main())
