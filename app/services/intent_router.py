from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import IntentResult


class IntentGateway:
    def __init__(self , fast_llm : ChatOpenAI):
        """
        初始化意图网关。
        """
        # 初始模型

        self.fast_llm = fast_llm

        # 绑定结构化输出
        self.router_chain = self.fast_llm.with_structured_output(IntentResult)

        # 使用 Few-Shot Prompting 规范输出边界
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个毫秒级的语音面试意图分类器。
你的唯一任务是：根据【当前考点】和【用户原话】，精准输出意图分类 (intent) 并提取超纲技术名词 (extracted_novel_concepts)。
以JSON格式返回结果
【分类与提取基准示例】：
例1：
[当前考点]: HashMap的扩容机制
[用户原话]: "当元素个数超过阈值就会扩容。为了防止多线程死循环，1.8改成尾插法了。"
-> {{"intent": "ANSWER", "extracted_novel_concepts": ["多线程", "尾插法"]}}

例2：
[当前考点]: HashMap的扩容机制
[用户原话]: "底层忘了，但我之前做秒杀系统用过Redis分布式锁，能聊聊那个吗？"
-> {{"intent": "SHIFT", "extracted_novel_concepts": ["Redis分布式锁"]}}

例3：
[当前考点]: JVM垃圾回收
[用户原话]: "不好意思，您刚才问的是CMS还是G1？"
-> {{"intent": "CLARIFY", "extracted_novel_concepts": ["CMS", "G1"]}}

例4：
[当前考点]: 数据库事务隔离级别
[用户原话]: "呃...这个...您稍等我想一下啊..."
-> {{"intent": "THINKING", "extracted_novel_concepts":[]}}

严格根据上述标准，对最新输入进行极速诊断。"""),
            ("user", "[当前考点]: {current_topic}\n[用户原话]: {user_text}")
        ])

        self.pipeline = self.prompt | self.router_chain

    async def analyze(self, current_topic: str, user_text: str) -> IntentResult:
        """
        执行意图诊断，返回结构化的 IntentResult
        """
        # 容错处理：如果用户没说话或 VAD 截断为空
        if not user_text or len(user_text.strip()) < 2:
            return IntentResult(intent="THINKING", extracted_novel_concepts=[])

        try:
            result: IntentResult = await self.pipeline.ainvoke({
                "current_topic": current_topic,
                "user_text": user_text
            })
            return result
        except Exception as e:
            # 极限兜底：如果 LLM API 抽风报错，默认当作正常答题放行，交由底层的 Evaluator 去给极低分
            print(f"[IntentGateway Error]: {e}")
            return IntentResult(intent="ANSWER", extracted_novel_concepts=[])


# ==========================================
# 本地极速测试脚本
# ==========================================
if __name__ == "__main__":
    import os
    import asyncio

    gateway = IntentGateway()


    async def test():
        res1 = await gateway.analyze("线程池参数",
                                     "核心线程满了进队列，队列满了再开最大线程。对了，如果有 ForkJoinPool 的需求场景该怎么设参数？")
        print(f"深入追问测试: {res1.model_dump()}")

        res2 = await gateway.analyze("TCP三次握手",
                                     "网络这块我不熟，但我平时 Spring 框架里面的 AOP 用的比较多。")
        print(f"转移话题测试: {res2.model_dump()}")


    asyncio.run(test())