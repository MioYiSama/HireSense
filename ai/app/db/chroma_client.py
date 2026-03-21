import asyncio
import json
import pickle
import sqlite3
from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.api.configuration import CollectionConfigurationInternal
from chromadb.config import Settings
from chromadb.segment.impl.vector.local_persistent_hnsw import PersistentData

COLLECTION_NAME = "interview_knowledge_base"
CHROMA_TELEMETRY_IMPL = "app.db.chroma_telemetry.NoOpProductTelemetry"



class ChromaClient:
    def __init__(self, persist_directory, bge_embedding_function):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._repair_legacy_collection_configs()
        self._repair_legacy_hnsw_metadata()

        # 建立本地持久化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl=CHROMA_TELEMETRY_IMPL,
                chroma_telemetry_impl=CHROMA_TELEMETRY_IMPL,
            ),
        )
        # 加载embedding模型
        self.bge_embedding_function = bge_embedding_function
        # 获取集合
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.bge_embedding_function
        )

    def _repair_legacy_collection_configs(self) -> None:
        sqlite_path = self.persist_directory / "chroma.sqlite3"
        if not sqlite_path.exists():
            return

        default_config_json = CollectionConfigurationInternal().to_json_str()
        updated_collections = []

        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            try:
                rows = cursor.execute(
                    "SELECT id, name, config_json_str FROM collections"
                ).fetchall()
            except sqlite3.OperationalError:
                return

            for collection_id, name, config_json_str in rows:
                if not self._collection_config_needs_migration(config_json_str):
                    continue

                cursor.execute(
                    "UPDATE collections SET config_json_str = ? WHERE id = ?",
                    (default_config_json, collection_id),
                )
                updated_collections.append(name)

            if updated_collections:
                conn.commit()
                repaired_names = ", ".join(updated_collections)
                print(
                    f"[Chroma] Repaired legacy collection configuration for: {repaired_names}"
                )

    def _repair_legacy_hnsw_metadata(self) -> None:
        sqlite_path = self.persist_directory / "chroma.sqlite3"
        if not sqlite_path.exists():
            return

        segment_dimensions = self._load_vector_segment_dimensions(sqlite_path)
        repaired_segments = []

        for segment_id, dimensionality in segment_dimensions.items():
            metadata_path = self.persist_directory / segment_id / "index_metadata.pickle"
            if not metadata_path.exists():
                continue

            try:
                with metadata_path.open("rb") as metadata_file:
                    persisted = pickle.load(metadata_file)
            except Exception:
                continue

            updated = None
            if isinstance(persisted, dict):
                updated = self._persistent_data_from_legacy_dict(persisted, dimensionality)
            elif hasattr(persisted, "dimensionality") and getattr(persisted, "dimensionality", None) is None:
                if dimensionality is not None and getattr(persisted, "id_to_label", {}):
                    persisted.dimensionality = dimensionality
                    updated = persisted

            if updated is None:
                continue

            with metadata_path.open("wb") as metadata_file:
                pickle.dump(updated, metadata_file, pickle.HIGHEST_PROTOCOL)
            repaired_segments.append(segment_id)

        if repaired_segments:
            repaired_list = ", ".join(repaired_segments)
            print(f"[Chroma] Repaired legacy HNSW metadata for segments: {repaired_list}")

    @staticmethod
    def _load_vector_segment_dimensions(sqlite_path: Path) -> dict[str, Optional[int]]:
        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            try:
                rows = cursor.execute(
                    """
                    SELECT segments.id, collections.dimension
                    FROM segments
                    JOIN collections ON collections.id = segments.collection
                    WHERE segments.scope = 'VECTOR'
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                return {}

        return {segment_id: dimension for segment_id, dimension in rows}

    @staticmethod
    def _persistent_data_from_legacy_dict(
        payload: dict, dimensionality: Optional[int]
    ) -> PersistentData:
        id_to_label = payload.get("id_to_label") or {}
        label_to_id = payload.get("label_to_id") or {}
        id_to_seq_id = payload.get("id_to_seq_id") or {}
        resolved_dimensionality = payload.get("dimensionality")
        if resolved_dimensionality is None and id_to_label:
            resolved_dimensionality = dimensionality

        persistent_data = PersistentData(
            dimensionality=resolved_dimensionality,
            total_elements_added=payload.get("total_elements_added", len(id_to_label)),
            id_to_label=id_to_label,
            label_to_id=label_to_id,
            id_to_seq_id=id_to_seq_id,
        )
        persistent_data.max_seq_id = payload.get("max_seq_id")
        return persistent_data

    @staticmethod
    def _collection_config_needs_migration(config_json_str: Optional[str]) -> bool:
        if not config_json_str or not config_json_str.strip():
            return True

        try:
            config_json = json.loads(config_json_str)
            CollectionConfigurationInternal.from_json(config_json)
        except Exception:
            return True

        return False

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


