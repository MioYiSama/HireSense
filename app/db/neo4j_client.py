import asyncio
from neo4j import AsyncGraphDatabase
from typing import Dict, Optional, Any, List


class Neo4jClient:
    def __init__(self, uri, user, password):
        self.driver = AsyncGraphDatabase.driver(uri,auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def get_question_brief(self, concept_name : str) -> list:
        """
        获取某考点的短题干，用于喂给 LLM 向用户发问。
        """
        try:
            if concept_name == "No result":
                return [{"brief":None,"q_id":None}]

            cypher="""
                   MATCH (c:Concept {name:$concept})-[:HAS_QUESTION]->(q:Question)
                   RETURN q.brief AS brief , q.q_id AS q_id
                   LIMIT 5
            """

            async with self.driver.session() as session:
                result = await session.run(cypher, concept=concept_name)
                recode = await result.data()
                return recode if recode else [{"brief":None,"q_id":None}]
        except Exception as e:
            print(f"[Neo4j Error] get_question_brief failed for {concept_name}: {e}")
            return [{"brief":None,"q_id":None}]


    async def get_batch_questions_brief(self, concept_list: List[str]):
        """
        获取批量考点的短题干，用于喂给 LLM 向用户发问。
        """
        try:
            if not concept_list:
                return [{"concept" : None, "question_info": None}]

            question_menu = []
            for concept in concept_list:
                result = await self.get_question_brief(concept_name=concept)
                item = {"concept": concept, "question_info":result}
                question_menu.append(item)

            return question_menu
        except Exception as e:
            print(f"[Neo4j Error] get_batch_questions_brief failed: {e}")
            return [{"concept" : None, "question_info": None}]



    async def get_icebreaker_concept(self, resume_concepts: List[str], visited_concepts: List[str]) -> list:
        """
        面试第一题（冷启动）。或者当用户想要跳转的内容未被找到时
        强制优先从候选人简历中提取属于该领域的初级节点。
        """
        try:
            cypher_priority_1 = """
                MATCH (c:Concept)-[:BELONGS_TO_DOMAIN]->(root:Concept)
                WHERE (c.name IN $resume_concepts OR root.name IN $resume_concepts)
                AND (NOT (c.name IN $visited_list) OR $visited_list IS NULL)
                OPTIONAL MATCH ()-[r:LEADS_TO]->(c)
                WITH c, count(r) AS in_degree
                ORDER BY in_degree ASC
                RETURN c.name AS concept LIMIT 3
            """
            async with self.driver.session() as session:
                result_1 = await session.run(cypher_priority_1, resume_concepts=resume_concepts, visited_list=visited_concepts)
                recode_1 = await result_1.data()
                if recode_1 :
                    return [c["concept"] for c in recode_1 if isinstance(c, dict) and "concept" in c]

                cypher_priority_2 = """
                               MATCH (c:Concept)-[:BELONGS_TO_DOMAIN]->(root:Concept)
                               WHERE NOT ()-[:LEADS_TO]->(c)
                               RETURN c.name AS concept LIMIT 3
                           """


                result_2 = await session.run(cypher_priority_2)
                recode_2 = await result_2.data()
                if recode_2:
                    return [c["concept"] for c in recode_2 if isinstance(c, dict) and "concept" in c]

                else:
                    return ["No result"]
        except Exception as e:
            print(f"[Neo4j Error] get_icebreaker_concept failed: {e}")
            return ["No result"]


    # 接口 话题跳跃与图谱跃迁（核心）
    async def verify_and_route_novel_concepts(self, concept_list: List[str]) -> list:
        """
        维度 2 处理。用户抛出新想法，Chroma 已将其对齐为图谱标准概念列表 aligned_concepts。
        判断这些概念在图谱中是否存在，以及它们和当前考点的关系。
        """
        try:
            if not concept_list:
                return ["No result"]
            cypher = """
                     UNWIND $concepts AS target_name
                     MATCH (target:Concept {name: target_name})
                     RETURN target.name AS concept
                     LIMIT 5
                 """

            async with self.driver.session() as session:
                results = await session.run(cypher, concepts=concept_list)
                recodes = await results.data()
                if recodes:
                    # 添加类型检查
                    return [c["concept"] for c in recodes if isinstance(c, dict) and "concept" in c]

                else :
                    return ["No result"]
        except Exception as e:
            print(f"[Neo4j Error] verify_and_route_novel_concepts failed: {e}")
            return ["No result"]



    # 接口 图谱多维弱剪枝（核心）
    async def get_action_space_candidates(self, current_concept: str, visited: List[str], resume_concepts: List[str],
            limit_fwd: int,
            limit_sib: int,
            limit_bwd: int
    ) :
        """
        进行问题跃迁
        根据知识掌握度计算检索配额，并发执行查询，并根据简历命中率进行权重排序。
        """
        try:
            tasks = []
            keys = []

            if limit_bwd > 0:
                async def query_bwd():
                    cypher_bwd = """
                        MATCH (prev:Concept)-[:LEADS_TO]->(c:Concept {name: $topic})
                        WHERE NOT (prev.name IN $visited)
                        WITH prev, CASE WHEN prev.name IN $resume THEN 1 ELSE 0 END AS weight
                        ORDER BY weight DESC LIMIT $limit
                        RETURN prev.name AS candidate
                    """
                    async with self.driver.session() as session:
                        result = await session.run(cypher_bwd, topic=current_concept, visited=visited, resume=resume_concepts, limit=limit_bwd)
                        return await result.data()

                tasks.append(query_bwd())
                keys.append("问题降级")

            if limit_fwd > 0:
                async def query_fwd():
                    cypher_fwd = """
                        MATCH (c:Concept {name: $topic})-[:LEADS_TO]->(next:Concept)
                        WHERE NOT (next.name IN $visited)
                        WITH next, CASE WHEN next.name IN $resume THEN 1 ELSE 0 END AS weight
                        ORDER BY weight DESC LIMIT $limit
                        RETURN next.name AS candidate
                    """
                    async with self.driver.session() as session:
                        result = await session.run(cypher_fwd, topic=current_concept, visited=visited, resume=resume_concepts, limit=limit_fwd)
                        return await result.data()

                tasks.append(query_fwd())
                keys.append("问题深入")

            if limit_sib > 0:
                async def query_sib():
                    cypher_sib = """
                        MATCH (c:Concept {name: $topic})-[:RELATED_TO]-(bro:Concept)
                        WHERE NOT (bro.name IN $visited)
                          AND bro.name <> $topic
                        WITH bro, CASE WHEN bro.name IN $resume THEN 1 ELSE 0 END AS weight
                        ORDER BY weight DESC
                        LIMIT $limit
                        RETURN bro.name AS candidate
                    """
                    async with self.driver.session() as session:
                        result = await session.run(cypher_sib, topic=current_concept, visited=visited, resume=resume_concepts, limit=limit_sib)
                        return await result.data()

                tasks.append(query_sib())
                keys.append("问题平移")

            results = await asyncio.gather(*tasks)

            menu = {}
            total_candidates = 0
            for key, recode in zip(keys, results):
                # 添加类型检查
                candidates = [c["candidate"] for c in recode if isinstance(c, dict) and "candidate" in c]
                if candidates:
                    concept_and_questions = await self.get_batch_questions_brief(concept_list=candidates)
                    menu[key] = concept_and_questions
                    total_candidates += len(candidates)

            if total_candidates == 0:
                fallback_cypher = """
                    MATCH (c:Concept)-[:BELONGS_TO_DOMAIN]->(root:Concept)
                    WHERE (c.name IN $resume_concepts OR root.name IN $resume_concepts)
                    AND NOT (c.name IN $visited)
                    OPTIONAL MATCH ()-[r:LEAD_TO]->(c)
                    WITH c, count(r) AS in_degree
                    ORDER BY in_degree ASC
                    RETURN c.name AS candidate LIMIT 3
                """
                async with self.driver.session() as session:
                    fb_res = await session.run(
                        fallback_cypher,
                        visited=visited,
                        resume_concepts=resume_concepts
                    )
                    fb_records = await fb_res.data()
                    # 添加类型检查
                    candidates = [r["candidate"] for r in fb_records if isinstance(r, dict) and "candidate" in r]
                    concept_and_questions = await self.get_batch_questions_brief(concept_list=candidates)
                    menu["全局跳跃 (当前方向已耗尽)"] = concept_and_questions

            return menu
        except Exception as e:
            print(f"[Neo4j Error] get_action_space_candidates failed: {e}")
            return {}



























