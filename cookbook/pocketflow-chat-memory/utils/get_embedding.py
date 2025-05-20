import os
import numpy as np
from openai import OpenAI


def get_embedding(text):
    # 创建OpenAI客户端，读取API密钥和API地址（可通过环境变量设置）
    client = OpenAI(
        api_key=os.environ.get("SF_API_KEY", "YOUR_API_KEY"),
        base_url=os.environ.get("SF_BASE_URL", "https://api.openai.com/v1"),
    )

    # 调用API获取文本的向量表示（embedding）
    response = client.embeddings.create(model="BAAI/bge-m3", input=text)

    # 从API返回结果中提取embedding向量
    embedding = response.data[0].embedding

    print(f"Embedding shape: {len(embedding)}")

    # 转换为numpy数组，方便后续数值计算
    return np.array(embedding, dtype=np.float32)


if __name__ == "__main__":
    # 测试embedding函数
    text1 = "The quick brown fox jumps over the lazy dog."
    text2 = "Python is a popular programming language for data science."
    text3 = "Python is a popular programming language for AI."

    emb1 = get_embedding(text3)
    emb2 = get_embedding(text2)

    print(f"emb2: {emb2}")

    # 打印embedding的形状（维度）
    print(f"Embedding 1 shape: {emb1.shape}")
    print(f"Embedding 2 shape: {emb2.shape}")

    # 计算两个embedding的点积，作为文本相似度的简单度量
    similarity = np.dot(emb1, emb2)
    print(f"Similarity between texts: {similarity:.4f}")
