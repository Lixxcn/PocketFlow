import asyncio
from pocketflow import AsyncNode, AsyncFlow
from utils import call_llm

# 定义人物1的系统提示词 (可手动编辑)
AGENT1_SYSTEM_PROMPT = "你是一个友善的AI助手，喜欢帮助别人。"

# 定义人物2的系统提示词 (可手动编辑)
AGENT2_SYSTEM_PROMPT = "你是一个好奇的AI研究员，喜欢提问和探索新知识。"


class ChatAgent1(AsyncNode):
    async def prep_async(self, shared):
        # 等待来自 Agent2 的消息 (或初始消息)
        message = await shared["agent1_queue"].get()
        if message == "CHAT_END":
            return None
        return shared["conversation_history"], AGENT1_SYSTEM_PROMPT

    async def exec_async(self, inputs):
        if inputs is None:
            return None
        history, system_prompt = inputs

        # 构建发送给 LLM 的 prompt，包含系统提示词和对话历史
        prompt = f"{system_prompt}\n\n对话历史:\n"
        for role, msg in history:
            prompt += f"{role}: {msg}\n"
        prompt += "ChatAgent1: "  # 提示 LLM 以 Agent1 的身份回复

        response = call_llm(prompt)
        print(f"\n\nAgent1: {response}")
        return response

    async def post_async(self, shared, prep_res, exec_res):
        if exec_res is None:
            return "end"

        # 更新对话历史
        shared["conversation_history"].append(("Agent1", exec_res))

        # 检查是否达到最大轮数
        shared["round_count"] += 1
        if shared["round_count"] >= 3:
            print("达到最大聊天轮数，聊天结束。")
            await shared["agent2_queue"].put("CHAT_END")  # 通知 Agent2 结束
            return "end"

        # 将回复发送给 Agent2
        await shared["agent2_queue"].put(exec_res)
        return "continue"


class ChatAgent2(AsyncNode):
    async def prep_async(self, shared):
        # 等待来自 Agent1 的消息
        message = await shared["agent2_queue"].get()
        if message == "CHAT_END":
            return None
        return shared["conversation_history"], AGENT2_SYSTEM_PROMPT

    async def exec_async(self, inputs):
        if inputs is None:
            return None
        history, system_prompt = inputs

        # 构建发送给 LLM 的 prompt，包含系统提示词和对话历史
        prompt = f"{system_prompt}\n\n对话历史:\n"
        for role, msg in history:
            prompt += f"{role}: {msg}\n"
        prompt += "ChatAgent2: "  # 提示 LLM 以 Agent2 的身份回复

        response = call_llm(prompt)
        print(f"\n\nAgent2: {response}")
        return response

    async def post_async(self, shared, prep_res, exec_res):
        # 检查 prep_async 是否返回 None (表示接收到结束信号)
        if prep_res is None:
            # 如果接收到结束信号，也向 Agent1 发送结束信号
            await shared["agent1_queue"].put("CHAT_END")
            return "end"

        if exec_res is None:
            return "end"

        # 更新对话历史
        shared["conversation_history"].append(("Agent2", exec_res))

        # 检查是否达到最大轮数 (只需在一个 Agent 中检查即可)
        # shared["round_count"] += 1 # 避免重复计数

        # 将回复发送给 Agent1
        await shared["agent1_queue"].put(exec_res)
        return "continue"


async def main():
    print("=========== AI 智能体聊天开始 ===========")

    # 设置共享状态
    shared = {
        "conversation_history": [],  # 存储对话历史 [(role, message)]
        "round_count": 0,  # 聊天轮数计数
        "agent1_queue": asyncio.Queue(),  # Agent1 接收消息的队列
        "agent2_queue": asyncio.Queue(),  # Agent2 接收消息的队列
    }

    # 初始化对话，Agent1 先开始
    initial_message = "你好，我们来聊聊天吧！"
    shared["conversation_history"].append(("Agent1", initial_message))
    await shared["agent2_queue"].put(initial_message)  # 将第一条消息放入 Agent2 的队列

    # 创建节点和流程
    agent1 = ChatAgent1()
    agent2 = ChatAgent2()

    # 设置流程循环
    agent1_flow = AsyncFlow(start=agent1)
    agent2_flow = AsyncFlow(start=agent2)

    # 连接节点，形成对话循环
    agent1 - "continue" >> agent2
    agent2 - "continue" >> agent1

    # 运行两个智能体流程
    await asyncio.gather(agent1_flow.run_async(shared), agent2_flow.run_async(shared))

    print("=========== AI 智能体聊天结束 ===========")


if __name__ == "__main__":
    asyncio.run(main())
