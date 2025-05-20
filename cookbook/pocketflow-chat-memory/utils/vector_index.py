import numpy as np
import faiss


def create_index(dimension=1536):
    # 创建一个FAISS的L2距离索引，dimension为向量维度
    return faiss.IndexFlatL2(dimension)


def add_vector(index, vector):
    # 确保vector是numpy数组，并且形状符合FAISS要求
    vector = np.array(vector).reshape(1, -1).astype(np.float32)

    # print("vector.shape:", vector.shape, "index.d:", index.d)
    assert (
        vector.shape[1] == index.d
    ), f"Embedding dim {vector.shape[1]} != index dim {index.d}"

    # 将向量添加到索引中
    index.add(vector)

    # 返回该向量在索引中的位置（index.ntotal为索引中向量总数）
    return index.ntotal - 1


def search_vectors(index, query_vector, k=1):
    """查找与查询向量最相似的k个向量

    参数:
        index: FAISS索引
        query_vector: 查询向量（numpy数组或list）
        k: 返回结果的数量（默认1）

    返回:
        tuple: (indices, distances)
            - indices: 索引中的位置列表
            - distances: 对应的距离列表
    """
    # 确保不会检索超过索引中已有的向量数量
    k = min(k, index.ntotal)
    if k == 0:
        return [], []

    # 确保查询向量是numpy数组，并且形状符合FAISS要求
    query_vector = np.array(query_vector).reshape(1, -1).astype(np.float32)

    # 在索引中进行搜索
    distances, indices = index.search(query_vector, k)

    return indices[0].tolist(), distances[0].tolist()


# 示例用法
if __name__ == "__main__":
    # 创建一个新的索引
    index = create_index(dimension=3)

    # 添加一些随机向量，并单独记录它们
    items = []
    for i in range(5):
        vector = np.random.random(3)
        # print("vector:", vector)
        position = add_vector(index, vector)
        items.append(f"Item {i}")
        print(f"Added vector at position {position}")

    print(f"Index contains {index.ntotal} vectors")

    # 检索与查询向量最相似的向量
    query = np.random.random(3)
    indices, distances = search_vectors(index, query, k=2)

    print("Query:", query)
    print("Found indices:", indices)
    print("Distances:", distances)
    print("Retrieved items:", [items[idx] for idx in indices])
