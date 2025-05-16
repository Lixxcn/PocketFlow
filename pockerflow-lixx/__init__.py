import asyncio, warnings, copy, time


class BaseNode:
    """
    所有节点类的基类。
    定义了节点的基本属性（参数、后继节点）和核心方法（准备、执行、后处理）。
    """

    def __init__(self):
        # 初始化节点的参数和后继节点字典
        self.params = {}
        self.successors = {}

    def set_params(self, params):
        """设置节点的参数。"""
        self.params = params

    def next(self, node, action="default"):
        """
        定义节点的下一个节点。
        :param node: 下一个节点实例。
        :param action: 触发转换到下一个节点的动作名称，默认为 "default"。
        :return: 下一个节点实例，方便链式调用。
        """
        if action in self.successors:
            warnings.warn(f"Overwriting successor for action '{action}'")
        self.successors[action] = node
        return node

    def prep(self, shared):
        """
        准备阶段：在执行主要逻辑前调用。
        子类可以重写此方法以准备执行所需的数据。
        :param shared: 流程中共享的数据对象。
        :return: 准备结果，将传递给 exec 方法。
        """
        pass  # 默认不执行任何操作

    def exec(self, prep_res):
        """
        执行阶段：节点的主要业务逻辑。
        子类必须重写此方法。
        :param prep_res: prep 方法的返回值。
        :return: 执行结果，将传递给 post 方法。
        """
        pass  # 默认不执行任何操作

    def post(self, shared, prep_res, exec_res):
        """
        后处理阶段：在执行主要逻辑后调用。
        子类可以重写此方法以处理执行结果或清理资源。
        :param shared: 流程中共享的数据对象。
        :param prep_res: prep 方法的返回值。
        :param exec_res: exec 方法的返回值。
        :return: 后处理结果，通常是 exec_res 或其修改版，也可能是触发下一个节点的 action。
        """
        pass  # 默认不执行任何操作

    def _exec(self, prep_res):
        """内部执行方法，直接调用 exec。可被子类（如 BatchNode）重写以修改执行行为。"""
        return self.exec(prep_res)

    def _run(self, shared):
        """
        内部运行方法，按顺序调用 prep, _exec, post。
        这是单个节点执行的标准流程。
        """
        prep_result = self.prep(shared)
        exec_result = self._exec(prep_result)
        post_result = self.post(shared, prep_result, exec_result)
        return post_result

    def run(self, shared):
        """
        公开的运行节点方法。
        如果节点有后继节点，会发出警告，因为单个节点运行不处理流程转换。
        """
        if self.successors:
            warnings.warn("Node won't run successors. Use Flow.")
        return self._run(shared)

    def __rshift__(self, other_node):
        """重载 >> 运算符，使其等同于调用 next(other_node) 方法，用于链式定义流程。"""
        return self.next(other_node)

    def __sub__(self, action_name):
        """
        重载 - 运算符，用于创建条件转换。
        例如: node1 - "success" >> node2
        :param action_name: 字符串类型的动作名称。
        :return: _ConditionalTransition 实例，用于后续的 >> 操作。
        """
        if isinstance(action_name, str):
            return _ConditionalTransition(self, action_name)
        raise TypeError("Action must be a string")


class _ConditionalTransition:
    """
    辅助类，用于实现条件转换的语法糖 (node - "action" >> next_node)。
    """

    def __init__(self, source_node, action_name):
        # 源节点
        self.src = source_node
        # 转换的动作名称
        self.action = action_name

    def __rshift__(self, target_node):
        """
        重载 >> 运算符，将目标节点设置为源节点在特定动作下的后继节点。
        """
        return self.src.next(target_node, self.action)


class Node(BaseNode):
    """
    标准的同步节点，增加了重试和回退逻辑。
    """

    def __init__(self, max_retries=1, wait=0):
        """
        :param max_retries: 执行失败时的最大重试次数。
        :param wait: 每次重试前的等待时间（秒）。
        """
        super().__init__()
        self.max_retries = max_retries
        self.wait = wait
        self.cur_retry = 0  # 当前重试次数

    def exec_fallback(self, prep_res, exception):
        """
        执行回退逻辑：当 exec 方法在所有重试后仍然失败时调用。
        默认行为是重新抛出异常。
        :param prep_res: prep 方法的返回值。
        :param exception: exec 方法抛出的最后一个异常。
        """
        raise exception

    def _exec(self, prep_res):
        """
        内部执行方法，包含重试逻辑。
        会尝试执行 self.exec 最多 self.max_retries 次。
        """
        for self.cur_retry in range(self.max_retries):
            try:
                return self.exec(prep_res)
            except Exception as e:
                if self.cur_retry == self.max_retries - 1:
                    # 最后一次重试失败，执行回退逻辑
                    return self.exec_fallback(prep_res, e)
                if self.wait > 0:
                    time.sleep(self.wait)  # 等待后重试


class BatchNode(Node):
    """
    批处理节点，其 _exec 方法会迭代处理输入项列表。
    """

    def _exec(self, items):
        """
        对输入列表中的每个项目调用父类（Node）的 _exec 方法。
        :param items: 一个项目列表。
        :return: 一个包含每个项目执行结果的列表。
        """
        # (items or []) 确保即使 items 为 None 也能安全迭代
        return [super(BatchNode, self)._exec(i) for i in (items or [])]


class Flow(BaseNode):
    """
    流程控制器，用于编排和执行一系列连接的节点。
    """

    def __init__(self, start_node=None):
        """
        :param start_node: 流程的起始节点。
        """
        super().__init__()
        self.start_node = start_node

    def start(self, start_node):
        """
        设置流程的起始节点。
        :param start_node: 起始节点实例。
        :return: 起始节点实例，方便链式调用。
        """
        self.start_node = start_node
        return start_node

    def get_next_node(self, current_node, action):
        """
        根据当前节点和上一个节点返回的动作，获取下一个要执行的节点。
        :param current_node: 当前执行完毕的节点。
        :param action: current_node._run() 返回的动作名称。
        :return: 下一个节点实例，如果找不到则为 None。
        """
        next_node = current_node.successors.get(
            action or "default"
        )  # 如果 action 为 None 或空字符串，则使用 "default"
        if not next_node and current_node.successors:
            # 如果没有找到对应的 action，但当前节点确实有后继节点定义，则发出警告
            warnings.warn(
                f"Flow ends: '{action}' not found in {list(current_node.successors.keys())}"
            )
        return next_node

    def _orch(self, shared, params=None):
        """
        内部编排逻辑：按顺序执行流程中的节点。
        :param shared: 流程中共享的数据对象。
        :param params: 传递给流程中每个节点的初始参数。
        :return: 流程中最后一个节点返回的动作。
        """
        current_node = copy.copy(self.start_node)  # 从起始节点的副本开始
        # (params or {**self.params}) 表示如果提供了 params 则使用它，否则使用 Flow 自身的 params
        # {**self.params} 是为了确保 Flow 自身的 params 也能被节点访问（如果 params 未提供或未覆盖）
        node_params = params or {**self.params}
        last_action = None

        while current_node:
            current_node.set_params(node_params)  # 为当前节点设置参数
            last_action = current_node._run(shared)  # 执行当前节点
            # 获取下一个节点，注意这里也使用 copy，避免修改原始流程定义
            current_node = copy.copy(self.get_next_node(current_node, last_action))
        return last_action

    def _run(self, shared):
        """
        内部运行方法，对于 Flow 而言，它会先执行自身的 prep，然后执行编排 _orch，最后执行 post。
        """
        prep_result = self.prep(shared)
        # Flow 的主要 "执行" 是编排其内部节点
        orch_result = self._orch(
            shared
        )  # 注意：Flow 的 prep_result 通常不直接传递给 _orch
        # Flow 的 post 方法接收 prep_result 和 _orch 的结果 (通常是最后一个节点的 action)
        return self.post(shared, prep_result, orch_result)

    def post(self, shared, prep_res, exec_res):
        """
        Flow 的 post 方法默认返回编排结果（通常是最后一个节点的 action）。
        """
        return exec_res


class BatchFlow(Flow):
    """
    批处理流程，其 prep 方法返回一个参数列表，流程会对每个参数执行一次完整的编排。
    """

    def _run(self, shared):
        """
        对于批处理流程，prep 返回一个参数列表。
        流程会对 prep 返回的每个参数字典执行一次完整的编排 (_orch)。
        """
        prep_results_list = self.prep(shared) or []  # prep 应返回一个参数字典的列表
        for batch_params in prep_results_list:
            # 合并 Flow 的全局参数和当前批次的参数，批次参数优先
            combined_params = {**self.params, **batch_params}
            self._orch(shared, combined_params)
        # BatchFlow 的 post 通常基于 prep 的结果，exec_res 在这里设为 None，因为执行是分散的
        return self.post(shared, prep_results_list, None)


class AsyncNode(Node):
    """
    异步节点，其核心方法 (prep, exec, post) 都是异步的。
    """

    async def prep_async(self, shared):
        """异步准备阶段。"""
        pass

    async def exec_async(self, prep_res):
        """异步执行阶段。"""
        pass

    async def exec_fallback_async(self, prep_res, exc):
        """异步执行回退逻辑。"""
        raise exc

    async def post_async(self, shared, prep_res, exec_res):
        """异步后处理阶段。"""
        pass

    async def _exec(self, prep_res):
        """内部异步执行方法，包含重试逻辑。"""
        for i in range(self.max_retries):
            try:
                return await self.exec_async(prep_res)
            except Exception as e:
                if i == self.max_retries - 1:
                    return await self.exec_fallback_async(prep_res, e)
                if self.wait > 0:
                    await asyncio.sleep(self.wait)

    async def run_async(self, shared):
        """公开的异步运行节点方法。"""
        if self.successors:
            warnings.warn("Node won't run successors. Use AsyncFlow.")
        return await self._run_async(shared)

    async def _run_async(self, shared):
        """内部异步运行方法，按顺序调用异步的 prep, _exec, post。"""
        prep_result = await self.prep_async(shared)
        exec_result = await self._exec(prep_result)
        post_result = await self.post_async(shared, prep_result, exec_result)
        return post_result

    def _run(self, shared):
        """同步 _run 在 AsyncNode 中不被支持，应使用 _run_async。"""
        raise RuntimeError("Use run_async for AsyncNode.")


class AsyncBatchNode(AsyncNode, BatchNode):
    """
    异步批处理节点。
    继承自 AsyncNode (提供异步能力) 和 BatchNode (提供批处理结构)。
    """

    async def _exec(self, items):
        """
        异步地对输入列表中的每个项目调用父类（AsyncNode）的 _exec 方法。
        """
        results = []
        for i in items or []:
            # super(AsyncBatchNode, self) 会调用 MRO 中 AsyncNode 的 _exec
            results.append(await super(AsyncBatchNode, self)._exec(i))
        return results


class AsyncParallelBatchNode(AsyncNode, BatchNode):
    """
    异步并行批处理节点。
    使用 asyncio.gather 并发执行所有批处理项。
    """

    async def _exec(self, items):
        """
        使用 asyncio.gather 并发执行列表中的所有异步任务。
        """
        if not items:
            return []
        # 为每个 item 创建一个异步任务
        tasks = [super(AsyncParallelBatchNode, self)._exec(i) for i in items]
        return await asyncio.gather(*tasks)


class AsyncFlow(Flow, AsyncNode):
    """
    异步流程控制器。
    继承自 Flow (提供流程编排逻辑) 和 AsyncNode (使其自身可以作为异步节点嵌入其他流程，并提供异步方法)。
    """

    async def _orch_async(self, shared, params=None):
        """
        内部异步编排逻辑。
        """
        current_node = copy.copy(self.start_node)
        node_params = params or {**self.params}
        last_action = None

        while current_node:
            current_node.set_params(node_params)
            if isinstance(current_node, AsyncNode):
                # 如果当前节点是异步节点，则异步运行它
                last_action = await current_node._run_async(shared)
            else:
                # 否则，同步运行它 (这在异步流程中通常不推荐，但框架支持)
                last_action = current_node._run(shared)
            current_node = copy.copy(self.get_next_node(current_node, last_action))
        return last_action

    async def _run_async(self, shared):
        """
        内部异步运行方法，对于 AsyncFlow。
        """
        # AsyncFlow 继承了 AsyncNode，所以它有 prep_async 和 post_async
        prep_result = await self.prep_async(shared)  # 调用 AsyncNode 的 prep_async
        orch_result = await self._orch_async(shared)
        # 调用 AsyncNode 的 post_async
        return await self.post_async(shared, prep_result, orch_result)

    async def post_async(self, shared, prep_res, exec_res):
        """
        AsyncFlow 的异步 post 方法，默认返回编排结果。
        继承自 AsyncNode。
        """
        return exec_res


class AsyncBatchFlow(AsyncFlow, BatchFlow):
    """
    异步批处理流程。
    prep_async 返回一个参数列表，流程会对每个参数异步地执行一次完整的编排。
    """

    async def _run_async(self, shared):
        """
        异步执行批处理流程。
        """
        # prep_async 来自 AsyncNode (通过 AsyncFlow 继承)
        prep_results_list = await self.prep_async(shared) or []
        for batch_params in prep_results_list:
            combined_params = {**self.params, **batch_params}
            # _orch_async 来自 AsyncFlow
            await self._orch_async(shared, combined_params)
        # post_async 来自 AsyncNode (通过 AsyncFlow 继承)
        return await self.post_async(shared, prep_results_list, None)


class AsyncParallelBatchFlow(AsyncFlow, BatchFlow):
    """
    异步并行批处理流程。
    并发执行所有批处理流程实例。
    """

    async def _run_async(self, shared):
        """
        使用 asyncio.gather 并发执行所有批处理流程的编排。
        """
        prep_results_list = await self.prep_async(shared) or []
        if not prep_results_list:
            return await self.post_async(shared, [], None)

        tasks = []
        for batch_params in prep_results_list:
            combined_params = {**self.params, **batch_params}
            # 为每个批次参数创建一个 _orch_async 任务
            tasks.append(self._orch_async(shared, combined_params))

        await asyncio.gather(*tasks)  # 并发执行所有编排任务
        return await self.post_async(shared, prep_results_list, None)
