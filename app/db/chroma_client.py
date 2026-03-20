import asyncio
import chromadb
from typing import Any, Dict, Optional, List, final
from chromadb.utils import embedding_functions
from app.core.config import EMBEDDING_MODEL,CHROMA_DATA



class ChromaClient:
    def __init__(self, persist_directory, bge_embedding_function):
        # 建立本地持久化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(path=persist_directory)
        # 加载embedding模型
        self.bge_embedding_function = bge_embedding_function
        # 获取集合
        self.collection = self.client.get_or_create_collection(
            name="interview_knowledge_base",
            embedding_function=self.bge_embedding_function
        )

    async def async_get_standard_answer(self, q_id : str):
        """
        获取该考点的标准答案。
         """
        def _get():
            return self.collection.get(
                where={"q_id" : q_id},
                limit=1
            )
        result = await asyncio.to_thread(_get)
        # print(result)
        if result and result.get("metadatas") and isinstance(result["metadatas"], list) and len(result["metadatas"]) > 0:
            return result["metadatas"][0].get("answer")
        return None


    async def async_align_entity(self, uncheck_concepts : List[str], limit_rate : float = 0.4) -> List[str]:
        """
        将concept纠正为与图谱定义一致的内容
        """
        try:
            def _query():
                return self.collection.query(
                    query_texts=uncheck_concepts,
                    n_results=1
                )

            results = await asyncio.to_thread(_query)

            final_ans = []
            for query_meta, distances in zip(results["metadatas"], results["distances"]):
                if not query_meta or not distances:
                    continue

                distance = distances[0]
                if distance is None:
                    continue  # 无距离值（精准过滤场景），跳过

                # 修复4：距离小于阈值时，提取concept（加get避免KeyError）
                if float(distance) < limit_rate:
                    # 添加类型检查
                    if isinstance(query_meta, list) and len(query_meta) > 0 and isinstance(query_meta[0], dict):
                        concept = query_meta[0].get("concept")
                        if concept:  # 过滤空concept
                            final_ans.append(concept)

            # 无符合条件的结果时，返回指定格式（和原逻辑一致）
            if not final_ans:
                return ["No result"]

            return final_ans
        except Exception as e:
            print(f"[Chroma Error] async_align_entity failed: {e}")
            return ["No result"]


    async def async_batch_align_concepts(self, raw_skills: List[str], threshold: float = 0.5) -> List[str]:
        """
        【业务场景】：简历技能点 -> 图谱标准概念 的批量对齐
        """
        try:
            if not raw_skills:
                return []

            def _batch_query():
                return self.collection.query(
                    query_texts=raw_skills,  # 例如 ["Redis做库存扣减", "熟练使用CHM"]
                    n_results=1
                )

            results = await asyncio.to_thread(_batch_query)
            matched_concepts = set()

            if results and results.get("distances") and results.get("metadatas"):
                for i in range(len(raw_skills)):
                    if i < len(results["distances"]) and i < len(results["metadatas"]):
                        distance = results["distances"][i][0]
                        # 此时的 distance 是极短 Query 与极短 Dense_Index 计算出的，极其精准
                        if float(distance) < threshold:
                            # 添加类型检查
                            metadata_item = results["metadatas"][i]
                            if isinstance(metadata_item, list) and len(metadata_item) > 0 and isinstance(metadata_item[0], dict):
                                matched_concept = metadata_item[0].get("concept")
                                if matched_concept:
                                    matched_concepts.add(matched_concept)

            return list(matched_concepts)
        except Exception as e:
            print(f"[Chroma Error] async_batch_align_concepts failed: {e}")
            return []



if __name__ == "__main__":
    q_id = "a9181648ddaf"
    async def main():
        chroma = ChromaClient()
        answer = await chroma.async_get_standard_answer(q_id= q_id)  # 加await
        print(answer)

    asyncio.run(main())

