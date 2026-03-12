import asyncio
import traceback
from typing import Any

from dify_client.async_client import AsyncKnowledgeBaseClient

from src.knowledge.base import FileStatus, KnowledgeBase
from src.utils import logger
from src.utils.datetime_utils import utc_isoformat


class DifyKB(KnowledgeBase):
    """基于 Dify API 的云端知识库服务"""

    @staticmethod
    def _unsupported_operation_error(operation: str) -> ValueError:
        return ValueError(f"Dify 知识库不支持{operation}")

    def __init__(self, work_dir: str, **kwargs):
        """
        初始化 Dify 知识库

        Args:
            work_dir: 工作目录
            **kwargs: 其他配置参数（在创建数据库时传入）
        """
        super().__init__(work_dir)

        # 存储每个数据库的 Dify 客户端 {db_id: AsyncKnowledgeBaseClient}
        self.clients: dict[str, AsyncKnowledgeBaseClient] = {}

        # 元数据锁
        self._metadata_lock = asyncio.Lock()

        # Segments 查询缓存 {(doc_id, positions_hash): (segments, timestamp)}
        # 缓存TTL从数据库配置中的 cache_ttl 参数读取
        self._segments_cache: dict[tuple[str, str], tuple[list[dict], float]] = {}

        logger.info("DifyKB initialized")

    @property
    def kb_type(self) -> str:
        """知识库类型标识"""
        return "dify"

    async def _create_kb_instance(self, db_id: str, kb_config: dict) -> Any:
        """
        创建 Dify 知识库实例（为该数据库创建独立的 client）

        Args:
            db_id: 数据库ID
            kb_config: 配置信息（由 create_database 传入的 kwargs）

        Returns:
            客户端实例
        """
        logger.info(f"Creating Dify client for {db_id}")

        if not (db_metadata := self.databases_meta.get(db_id)):
            raise ValueError(f"Database {db_id} not found")

        # 从元数据中的 dify_config 获取 Dify 配置
        # 注意：基类 create_database 将 kwargs 保存在 `metadata` 字段中
        inner_metadata = db_metadata.get("metadata", {}) or {}
        base_url = inner_metadata.get("dify_api_url", "https://api.dify.ai/v1")
        api_key = inner_metadata.get("dify_token")
        dataset_id = inner_metadata.get("dify_dataset_id")

        if not base_url:
            raise ValueError(f"Dify base_url is required in metadata for database {db_id}")
        if not api_key:
            raise ValueError(f"Dify API key is required in metadata for database {db_id}")
        if not dataset_id:
            raise ValueError(f"Dify dataset_id is required in metadata for database {db_id}")

        # 为该数据库创建独立的 client
        client = AsyncKnowledgeBaseClient(api_key=api_key, base_url=base_url, dataset_id=dataset_id)

        try:
            # 获取数据集详情，包含默认的 retrieval_model 配置
            response = await client.get_dataset(dataset_id)
            dataset_info = response.json()

            # 提取 retrieval_model_dict 作为默认配置
            if "retrieval_model_dict" in dataset_info:
                retrieval_model_dict = dataset_info["retrieval_model_dict"]
                logger.info(f"Retrieved default retrieval_model for {db_id}: {retrieval_model_dict}")

                # 保存到元数据中
                async with self._metadata_lock:
                    self.databases_meta[db_id]["dify_retrieval_model"] = retrieval_model_dict
                    await self._save_metadata()
            else:
                logger.warning(f"No retrieval_model_dict found in dataset {dataset_id}")

            logger.info(f"Dify connection validated for {db_id}")
        except Exception as e:
            logger.error(f"Failed to validate Dify connection for {db_id}: {e}")
            await client.aclose()
            raise

        # 存储 client
        self.clients[db_id] = client
        return client

    async def _initialize_kb_instance(self, instance: Any) -> None:
        """
        初始化 Dify 知识库实例（无需特殊初始化）

        Args:
            instance: 底层知识库实例
        """
        # Dify 不需要特殊初始化
        # 但我们需要从 processing_params 恢复 dify_document_id 到 files_meta 顶级字段
        # 因为数据库没有 dify_document_id 字段，我们将其存储在 processing_params 中
        for file_id, file_meta in self.files_meta.items():
            if not file_meta.get("dify_document_id"):
                params = file_meta.get("processing_params") or {}
                if isinstance(params, dict) and params.get("dify_document_id"):
                    self.files_meta[file_id]["dify_document_id"] = params["dify_document_id"]

    async def create_folder(self, db_id: str, folder_name: str, parent_id: str | None = None) -> dict:
        del db_id, folder_name, parent_id
        raise self._unsupported_operation_error("文件夹创建")

    async def move_file(self, db_id: str, file_id: str, new_parent_id: str | None) -> dict:
        del db_id, file_id, new_parent_id
        raise self._unsupported_operation_error("文件移动")

    async def delete_folder(self, db_id: str, folder_id: str) -> None:
        del db_id, folder_id
        raise self._unsupported_operation_error("文件夹删除")

    async def _get_client(self, db_id: str) -> AsyncKnowledgeBaseClient:
        """
        获取指定数据库的 Dify client（支持自动恢复）

        Args:
            db_id: 数据库ID

        Returns:
            AsyncKnowledgeBaseClient 实例

        Raises:
            ValueError: 如果数据库不存在或无法初始化
        """
        if db_id not in self.clients:
            # 专家提示：如果内存中没有 client（如重启后），尝试从元数据自动恢复
            logger.info(f"Dify client for {db_id} not initialized in memory, attempting to restore...")
            if db_id in self.databases_meta:
                await self._create_kb_instance(db_id, {})
            else:
                raise ValueError(f"Dify client for database {db_id} not initialized and no metadata found")
        return self.clients[db_id]

    async def index_file(self, db_id: str, file_id: str, operator_id: str | None = None) -> dict:
        """
        Index parsed file (Status: INDEXING -> INDEXED/ERROR_INDEXING)

        Args:
            db_id: Database ID
            file_id: File ID
            operator_id: ID of the user performing the operation

        Returns:
            Updated file metadata
        """
        if db_id not in self.databases_meta:
            raise ValueError(f"Database {db_id} not found")

        # Get file meta
        async with self._metadata_lock:
            if file_id not in self.files_meta:
                raise ValueError(f"File {file_id} not found")
            file_meta = self.files_meta[file_id]

            # Validate current status
            current_status = file_meta.get("status")
            allowed_statuses = {
                FileStatus.PARSED,
                FileStatus.ERROR_INDEXING,
                FileStatus.INDEXED,  # For re-indexing
                FileStatus.DONE,  # Legacy status
            }

            if current_status not in allowed_statuses:
                raise ValueError(
                    f"Cannot index file with status '{current_status}'. "
                    f"File must be parsed first (status should be one of: {', '.join(allowed_statuses)})"
                )

            # Check markdown file exists
            if not file_meta.get("markdown_file"):
                raise ValueError("File has not been parsed yet (no markdown_file)")

            # Clear previous error if any
            if "error" in file_meta:
                self.files_meta[file_id].pop("error", None)

            # Update status
            self.files_meta[file_id]["status"] = FileStatus.INDEXING
            self.files_meta[file_id]["updated_at"] = utc_isoformat()
            if operator_id:
                self.files_meta[file_id]["updated_by"] = operator_id
            await self._save_metadata()

            # Read processing params
            params = file_meta.get("processing_params", {}) or {}
            logger.debug(f"[index_file] file_id={file_id}, processing_params={params}")

        # Add to processing queue
        self._add_to_processing_queue(file_id)

        try:
            # Read markdown content
            markdown_content = await self._read_markdown_from_minio(file_meta["markdown_file"])
            filename = file_meta.get("filename", "untitled")

            # 获取该数据库的 client（异步获取，支持自动恢复）
            client = await self._get_client(db_id)

            # 判断是更新还是创建
            existing_doc_id = file_meta.get("dify_document_id")

            if existing_doc_id:
                # 重新索引：使用 update 而非 delete + create
                logger.info(f"Updating existing Dify document: {existing_doc_id}")
                response = await client.update_document_by_text(
                    document_id=existing_doc_id, name=filename, text=markdown_content
                )
            else:
                # 首次索引：创建新文档
                logger.info(f"Creating new Dify document for file: {file_id}")
                response = await client.create_document_by_text(name=filename, text=markdown_content)

            response_data = response.json()

            if response.status_code != 200:
                raise Exception(f"Dify API error: {response_data}")

            # 确定最终的 document_id
            if existing_doc_id:
                # update 场景：沿用原有 ID
                dify_document_id = existing_doc_id
                logger.info(f"Updated Dify document: {dify_document_id} for file {file_id}")
            else:
                # create 场景：从响应中提取新 ID
                dify_document_id = response_data.get("document", {}).get("id")
                if not dify_document_id:
                    raise Exception("Failed to get document_id from Dify response")
                logger.info(f"Created Dify document: {dify_document_id} for file {file_id}")

            # Update status
            async with self._metadata_lock:
                self.files_meta[file_id]["status"] = FileStatus.INDEXED
                self.files_meta[file_id]["dify_document_id"] = dify_document_id

                # 关键：保存到 processing_params 以持久化（因为数据库没有 dify_document_id 字段）
                if not self.files_meta[file_id].get("processing_params"):
                    self.files_meta[file_id]["processing_params"] = {}
                self.files_meta[file_id]["processing_params"]["dify_document_id"] = dify_document_id

                self.files_meta[file_id]["updated_at"] = utc_isoformat()
                if operator_id:
                    self.files_meta[file_id]["updated_by"] = operator_id
                await self._save_metadata()
                return self.files_meta[file_id]

        except Exception as e:
            logger.error(f"Indexing failed for {file_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            async with self._metadata_lock:
                self.files_meta[file_id]["status"] = FileStatus.ERROR_INDEXING
                self.files_meta[file_id]["error"] = str(e)
                self.files_meta[file_id]["updated_at"] = utc_isoformat()
                if operator_id:
                    self.files_meta[file_id]["updated_by"] = operator_id
                await self._save_metadata()
            raise

        finally:
            # Remove from processing queue
            self._remove_from_processing_queue(file_id)

    async def _expand_search_results(self, db_id: str, original_chunks: list[dict], n: int) -> list[dict]:
        """
        基于检索结果，自动补充上下文分片

        Args:
            db_id: 数据库ID
            original_chunks: 原始检索结果列表
            n: 前后补充的分片数量

        Returns:
            扩展后的分片列表（已按文档分组并重排序）
        """
        if n <= 0 or not original_chunks:
            return original_chunks

        # 1. 按文档分组
        docs_map = {}  # {file_id: [chunks]}
        doc_scores = {}  # {file_id: max_score}

        for chunk in original_chunks:
            meta = chunk.get("metadata", {})
            file_id = meta.get("file_id")
            if not file_id:
                continue

            if file_id not in docs_map:
                docs_map[file_id] = []
                doc_scores[file_id] = 0.0

            docs_map[file_id].append(chunk)
            doc_scores[file_id] = max(doc_scores[file_id], chunk.get("score", 0.0))

        if not docs_map:
            return original_chunks

        logger.info(f"Expanding context for {len(docs_map)} documents with n={n}")

        # 2. 并行获取全文分片
        # 我们使用 gather 并发获取所有涉及文档的内容
        file_ids = list(docs_map.keys())

        # 预先获取 client 以复用 connection
        try:
            client = await self._get_client(db_id)
        except Exception as e:
            logger.error(f"Failed to get client for expansion: {e}")
            return original_chunks

        # 预计算每个文档需要的 position 范围（用于优化分页）
        doc_required_positions = {}
        for file_id in file_ids:
            positions = set()
            for chunk in docs_map[file_id]:
                # 注意：position 现在对应 chunk_index
                pos = chunk.get("metadata", {}).get("chunk_index")
                if pos and isinstance(pos, int):
                    # 计算需要的范围：position ± n
                    for i in range(max(1, pos - n), pos + n + 1):
                        positions.add(i)
            doc_required_positions[file_id] = positions

        # 调用 _fetch_sorted_segments 时传递所需的 position 范围
        tasks = [
            self._fetch_sorted_segments(db_id, file_id, client, doc_required_positions.get(file_id))
            for file_id in file_ids
        ]

        # 注意：这里可能会有异常（如下载失败），我们需要处理
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 处理每个文档的扩展
        expanded_result = []

        # 按最高分降序排列文档，以此顺序构建最终结果
        sorted_file_ids = sorted(file_ids, key=lambda x: doc_scores[x], reverse=True)

        # 建立 file_id -> content_info 的映射
        doc_contents = {}
        for file_id, res in zip(file_ids, results):
            if isinstance(res, Exception):
                logger.warning(f"Failed to fetch content for expansion (file_id={file_id}): {res}")
            else:
                # 兼容原有结构，将 chunks 列表包装为 {"lines": chunks}
                doc_contents[file_id] = {"lines": res}

        for file_id in sorted_file_ids:
            # 如果获取全文失败，回退到使用原始 chunks
            content_info = doc_contents.get(file_id)
            if not content_info or not content_info.get("lines"):
                expanded_result.extend(docs_map[file_id])
                continue

            full_segments = content_info["lines"]  # List of {id, content, position, ...} (注意这里是 Dify 原生数据)
            # 建立 segment_id -> index 映射
            seg_id_to_idx = {seg["id"]: idx for idx, seg in enumerate(full_segments)}

            # 找到命中分片的索引
            hit_indices = set()
            hit_scores = {}  # index -> score

            for chunk in docs_map[file_id]:
                chunk_id = chunk["metadata"].get("chunk_id")
                chunk_index = chunk["metadata"].get("chunk_index")

                idx = -1

                # 优先 ID 匹配
                if chunk_id in seg_id_to_idx:
                    idx = seg_id_to_idx[chunk_id]
                # ID 匹配失败则尝试 Position 匹配 (Dify position 1-based, 假设 full_segments 是按 position 排序的)
                elif chunk_index and isinstance(chunk_index, int) and 0 < chunk_index <= len(full_segments):
                    # 这种按 index 的方式假设 full_segments 是完整的或者是按顺序的。
                    # 但因为我们用了 required_positions，full_segments 可能不是完整的，
                    # 所以最好是用 sort 后的 list 的内容去查。
                    # FIX: full_segments 是 _fetch_sorted_segments 返回的 Dify 原生片段列表。
                    # _fetch_sorted_segments 已经按 position 排序了。
                    # 如果是部分获取，index 就不等于 position - 1 了。
                    # 所以必须通过 chunk_id 来匹配。
                    # 如果没有 chunk_id (不太可能)，只能尝试找 position 属性

                    # 查找 matching segment by position property
                    for i, seg in enumerate(full_segments):
                        if seg.get("position") == chunk_index:
                            idx = i
                            break

                if idx != -1:
                    hit_indices.add(idx)
                    # 保留最高分
                    current_score = chunk.get("score", 0.0)
                    hit_scores[idx] = max(hit_scores.get(idx, 0.0), current_score)
                else:
                    pass

            # 计算扩展后的索引集合
            expanded_indices = set()
            total_len = len(full_segments)

            for idx in hit_indices:
                start = max(0, idx - n)
                end = min(total_len - 1, idx + n)
                for i in range(start, end + 1):
                    expanded_indices.add(i)

            # 排序索引
            sorted_indices = sorted(list(expanded_indices))

            # 构建新的 chunks
            doc_name = docs_map[file_id][0]["metadata"].get("source", "Unknown")

            for idx in sorted_indices:
                segment = full_segments[idx]  # Dify Native Segment
                seg_id = segment.get("id")
                content = segment.get("content")

                score = hit_scores.get(idx)

                new_chunk = {
                    "content": content,
                    "metadata": {
                        "source": doc_name,
                        "file_id": file_id,
                        "chunk_id": seg_id,
                        "chunk_index": segment.get("position"),
                        "is_extended": score is None,  # 标记是否为扩展分片
                    },
                    "score": score,
                }
                expanded_result.append(new_chunk)

        return expanded_result

    async def aquery(self, query_text: str, db_id: str, agent_call: bool = False, **kwargs) -> list[dict]:
        """
        异步查询知识库

        Args:
            query_text: 查询文本
            db_id: 数据库ID
            agent_call: 是否为 Agent 调用
            **kwargs: 其他查询参数

        Returns:
            查询结果列表
        """
        if db_id not in self.databases_meta:
            raise ValueError(f"Database {db_id} not found")

        query_params = self._get_query_params(db_id)
        # 合并查询参数
        merged_kwargs = {**query_params, **kwargs}

        try:
            # 获取该数据库的 client（异步获取，支持自动恢复）
            client = await self._get_client(db_id)

            # 获取 Dify 数据集的默认 retrieval_model 配置
            dify_default_retrieval = self.databases_meta[db_id].get("dify_retrieval_model", {})

            # 从用户参数或查询参数中获取配置
            top_k = int(merged_kwargs.get("recall_top_k", dify_default_retrieval.get("top_k", 10)))
            top_k = max(top_k, 1)

            similarity_threshold = float(
                merged_kwargs.get(
                    "similarity_threshold",
                    dify_default_retrieval.get("score_threshold", 0.0)
                    if dify_default_retrieval.get("score_threshold_enabled")
                    else 0.0,
                )
            )

            # 构建 Dify retrieval_model，优先使用 Dify 默认配置，允许用户参数覆盖
            retrieval_model = {
                "search_method": merged_kwargs.get(
                    "search_method", dify_default_retrieval.get("search_method", "semantic_search")
                ),
                "reranking_enable": merged_kwargs.get(
                    "use_reranker", dify_default_retrieval.get("reranking_enable", False)
                ),
                "top_k": top_k,
                "score_threshold_enabled": similarity_threshold > 0,
                "score_threshold": similarity_threshold if similarity_threshold > 0 else None,
            }

            # 如果 Dify 默认配置中有 reranking_mode，也包含进来
            if "reranking_mode" in dify_default_retrieval:
                retrieval_model["reranking_mode"] = dify_default_retrieval["reranking_mode"]

            # 如果 Dify 默认配置中有 reranking_model，也包含进来
            if "reranking_model" in dify_default_retrieval and dify_default_retrieval["reranking_model"]:
                retrieval_model["reranking_model"] = dify_default_retrieval["reranking_model"]

            # 如果是混合搜索且 Dify 配置中有 weights，包含进来
            if retrieval_model["search_method"] == "hybrid_search" and "weights" in dify_default_retrieval:
                retrieval_model["weights"] = dify_default_retrieval["weights"]

            logger.debug(f"Using retrieval_model: {retrieval_model}")

            import time

            t0 = time.time()

            # 调用 Dify retrieve API
            response = await client.retrieve(query=query_text, retrieval_model=retrieval_model)
            response_data = response.json()

            t1 = time.time()
            t1 - t0

            if response.status_code != 200:
                logger.error(f"Dify query error: {response_data}")
                return []

            # 转换结果格式
            records = response_data.get("records", [])
            retrieved_chunks = []

            for record in records:
                segment = record.get("segment", {})
                document = segment.get("document", {})
                score = record.get("score", 0.0)

                metadata = {
                    "source": document.get("name", "未知来源"),
                    "file_id": document.get("id"),
                    "chunk_id": segment.get("id"),
                    "chunk_index": segment.get("position"),
                }

                chunk = {"content": segment.get("content", ""), "metadata": metadata, "score": score}

                retrieved_chunks.append(chunk)

            logger.debug(f"Dify query response: {len(retrieved_chunks)} chunks found")

            # 上下文扩展
            context_size = int(merged_kwargs.get("context_size", 0))
            if context_size <= 0:
                return retrieved_chunks

            final_results = await self._expand_search_results(db_id, retrieved_chunks, context_size)
            t2 = time.time()
            expand_cost = t2 - t1
            logger.info(
                f"Dify query expansion: {len(retrieved_chunks)} -> {len(final_results)} chunks "
                f"(Time: {expand_cost:.3f}s)"
            )

            # 早期返回：无结果或不使用重排序
            if not final_results:
                return []

            use_local_reranker = bool(merged_kwargs.get("use_local_reranker", False))
            if not use_local_reranker:
                return final_results

            # 本地重排序逻辑 (Local Rerank)
            local_model_id = merged_kwargs.get("local_reranker_model")
            if not local_model_id:
                raise ValueError(
                    "Local reranker model must be specified when use_local_reranker=True. "
                    "Please provide local_reranker_model in query parameters."
                )

            try:
                from src.models.rerank import get_reranker

                reranker = get_reranker(local_model_id)
                try:
                    rerank_start = time.time()
                    documents_text = [chunk["content"] for chunk in final_results]
                    rerank_scores = await reranker.acompute_score([query_text, documents_text], normalize=True)

                    for chunk, rerank_score in zip(final_results, rerank_scores):
                        chunk["rerank_score"] = float(rerank_score)

                    final_results.sort(key=lambda item: item.get("rerank_score", item.get("score", 0.0)), reverse=True)
                    elapsed = time.time() - rerank_start
                    logger.info(f"Local reranking completed for {db_id} in {elapsed:.3f}s with model {local_model_id}")
                finally:
                    await reranker.aclose()

            except Exception as exc:  # noqa: BLE001
                logger.error(f"Local reranking failed: {exc}, falling back to expanded results")

            # 统一返回结果
            return final_results

        except Exception as e:
            logger.error(f"Dify query error: {e}, {traceback.format_exc()}")
            return []

    async def delete_file(self, db_id: str, file_id: str) -> None:
        """
        删除文件（支持云端联动删除）

        Args:
            db_id: 数据库ID
            file_id: 文件ID或Dify文档ID
        """
        # 获取该数据库的 client（异步获取，支持自动恢复）
        client = await self._get_client(db_id)

        # 1. 优先处理 Dify 云端文档删除
        dify_doc_id = None
        if file_id in self.files_meta:
            meta = self.files_meta[file_id]
            dify_doc_id = meta.get("dify_document_id")
            if not dify_doc_id:
                # 重启服务后，dify_document_id 存储在 processing_params 中
                dify_doc_id = meta.get("processing_params", {}).get("dify_document_id")
        else:
            # 专家设计：如果本地没记录，我们假设该 ID 本身就是 Dify 文档 ID（例如原生同步过来的）
            dify_doc_id = file_id

        if dify_doc_id:
            try:
                await client.delete_document(dify_doc_id)
                logger.info(f"Deleted Dify document: {dify_doc_id}")
            except Exception as e:
                # 盲删失败通常是因为文档在云端已经不存在或格式不正确，记录 Wanning 即可
                logger.warning(f"Could not delete Dify document {dify_doc_id} from cloud: {e}")

        # 3. 清理本地元数据和数据库记录
        async with self._metadata_lock:
            if file_id in self.files_meta:
                del self.files_meta[file_id]
                # 注意：_save_metadata 只做 upsert，需要显式删除数据库记录
                from src.repositories.knowledge_file_repository import KnowledgeFileRepository

                await KnowledgeFileRepository().delete(file_id)
                logger.info(f"Local metadata and database record for {file_id} cleared.")

    async def get_file_basic_info(self, db_id: str, file_id: str) -> dict:
        """获取文件基本信息（支持从 Dify 精准回退）"""
        # 1. 优先从本地元数据获取
        if file_id in self.files_meta:
            return {"meta": self.files_meta[file_id]}

        # 2. 专家设计：使用 get_document 从 Dify 云端获取精准元数据
        try:
            client = await self._get_client(db_id)
            response = await client.get_document(document_id=file_id)
            if response.status_code == 200:
                doc_detail = response.json()
                # 建立 Dify 状态到本地状态的转换
                dify_status = doc_detail.get("indexing_status", "completed")
                status_map = {
                    "completed": FileStatus.INDEXED,
                    "error": FileStatus.ERROR_INDEXING,
                    "parsing": FileStatus.INDEXING,
                    "splitting": FileStatus.INDEXING,
                    "indexing": FileStatus.INDEXING,
                }
                local_status = status_map.get(dify_status, FileStatus.INDEXED)

                logger.info(f"File {file_id} found on Dify cloud: {doc_detail.get('name')}")
                return {
                    "meta": {
                        "file_id": file_id,
                        "dify_document_id": file_id,
                        "filename": doc_detail.get("name", f"Cloud Doc ({file_id[:8]})"),
                        "status": local_status,
                        "database_id": db_id,
                        "created_at": doc_detail.get("created_at") or utc_isoformat(),
                        "is_cloud_native": True,
                        "word_count": doc_detail.get("word_count", 0),
                    }
                }
        except Exception as e:
            logger.debug(f"Precise cloud fallback failed for {file_id}: {e}")

        raise Exception(f"File not found locally or on Dify: {file_id}")

    async def _fetch_sorted_segments(
        self, db_id: str, dify_document_id: str, client=None, required_positions: set[int] | None = None
    ) -> list[dict]:
        """
        获取并解析文档分片（按 position 排序，支持按需分页）

        Args:
            db_id: 数据库ID
            dify_document_id: Dify文档ID
            client: 可选的客户端实例
            required_positions: 可选的所需 position 集合，用于优化分页获取
        """
        if not client:
            client = await self._get_client(db_id)

        # 从配置中读取优化参数
        query_params = self._get_query_params(db_id)
        merge_threshold = int(query_params.get("merge_threshold", 10))
        min_page_size = int(query_params.get("min_page_size", 20))
        max_page_size = int(query_params.get("max_page_size", 500))
        max_retries = int(query_params.get("max_retries", 3))
        cache_ttl = int(query_params.get("cache_ttl", 300))

        # 辅助函数：将 position 集合分组为连续区间
        def group_consecutive_positions(positions: set[int]) -> list[tuple[int, int]]:
            """将 position 集合分组为连续区间，例如 {3,4,5,6,7,87,88,89,90,91} → [(3,7), (87,91)]"""
            if not positions:
                return []
            sorted_positions = sorted(positions)
            intervals = []
            start = end = sorted_positions[0]
            for pos in sorted_positions[1:]:
                if pos == end + 1:
                    end = pos
                else:
                    intervals.append((start, end))
                    start = end = pos
            intervals.append((start, end))
            return intervals

        # 优化1：检查缓存
        if required_positions and cache_ttl > 0:
            import hashlib

            pos_hash = hashlib.md5(str(sorted(required_positions)).encode()).hexdigest()
            cache_key = (dify_document_id, pos_hash)

            if cache_key in self._segments_cache:
                cached_data, timestamp = self._segments_cache[cache_key]
                import time

                if time.time() - timestamp < cache_ttl:
                    logger.debug(f"Cache hit for document {dify_document_id} ({len(cached_data)} segments)")
                    return cached_data
                else:
                    # 缓存过期，删除
                    del self._segments_cache[cache_key]

        try:
            all_segments = []

            # 优化：如果指定了 required_positions，使用分组精确查询
            if required_positions:
                intervals = group_consecutive_positions(required_positions)
                logger.info(
                    f"Optimized query: {len(required_positions)} positions → {len(intervals)} intervals (before merge)"
                )

                # 优化1：合并间隔较小的相邻区间（避免重复查询相同页）
                merged_intervals = []
                for start_pos, end_pos in intervals:
                    if merged_intervals and start_pos - merged_intervals[-1][1] <= merge_threshold:
                        # 合并到上一个区间
                        merged_intervals[-1] = (merged_intervals[-1][0], end_pos)
                        logger.debug(
                            f"Merged interval: [{merged_intervals[-1][0]}, {end_pos}] (gap <= {merge_threshold})"
                        )
                    else:
                        merged_intervals.append((start_pos, end_pos))

                if len(merged_intervals) < len(intervals):
                    logger.info(f"Merged {len(intervals)} intervals → {len(merged_intervals)} intervals")

                # 优化2：收集所有查询参数，去重后批量查询
                query_tasks = {}  # {(page, limit): [intervals]}

                for start_pos, end_pos in merged_intervals:
                    interval_size = end_pos - start_pos + 1

                    # 动态计算 page_size（使用配置的最小/最大值）
                    dynamic_page_size = max(min(interval_size + 10, max_page_size), min_page_size)

                    # 计算需要的页码范围
                    start_page = (start_pos - 1) // dynamic_page_size + 1
                    end_page = (end_pos - 1) // dynamic_page_size + 1

                    logger.debug(
                        f"Interval [{start_pos}, {end_pos}] (size={interval_size}) → "
                        f"pages {start_page}-{end_page} (page_size={dynamic_page_size})"
                    )

                    # 收集查询参数
                    for page in range(start_page, end_page + 1):
                        key = (page, dynamic_page_size)
                        if key not in query_tasks:
                            query_tasks[key] = []
                        query_tasks[key].append((start_pos, end_pos))

                logger.info(f"Deduplicated queries: {len(query_tasks)} unique (page, limit) combinations")

                # 优化2：并行查询 + 优化3：重试机制（使用配置的重试次数）
                async def query_single_page(page: int, limit: int, interval_list: list[tuple[int, int]]):
                    """查询单个页面，带重试机制"""

                    for retry in range(max_retries):
                        try:
                            response = await client.query_segments(
                                document_id=dify_document_id, status="completed", params={"limit": limit, "page": page}
                            )
                            response_data = response.json()

                            if response.status_code == 200:
                                segments = response_data.get("data", [])

                                # 筛选所有相关区间的 segments
                                page_results = []
                                for start_pos, end_pos in interval_list:
                                    filtered_segments = [
                                        seg for seg in segments if start_pos <= seg.get("position", 0) <= end_pos
                                    ]
                                    page_results.extend(filtered_segments)

                                    logger.debug(
                                        f"Page {page} (limit={limit}): filtered {len(filtered_segments)} "
                                        f"for interval [{start_pos}, {end_pos}]"
                                    )

                                return page_results

                            elif response.status_code == 429:  # Rate limit
                                wait_time = 2**retry  # 指数退避
                                logger.warning(
                                    f"Rate limit on page {page}, retry {retry + 1}/{max_retries}, waiting {wait_time}s"
                                )
                                await asyncio.sleep(wait_time)
                            else:
                                logger.warning(
                                    f"Failed to query page {page} (status={response.status_code}): {response_data}"
                                )
                                if retry == max_retries - 1:
                                    raise Exception(f"Query failed after {max_retries} retries: {response_data}")
                                await asyncio.sleep(1)

                        except Exception as e:
                            if retry == max_retries - 1:
                                logger.error(f"Failed to query page {page} after {max_retries} retries: {e}")
                                raise
                            logger.warning(f"Error querying page {page}, retry {retry + 1}/{max_retries}: {e}")
                            await asyncio.sleep(1)

                    return []

                # 并行执行所有页查询
                tasks = [
                    query_single_page(page, limit, interval_list)
                    for (page, limit), interval_list in query_tasks.items()
                ]

                import time

                t_start = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                t_elapsed = time.time() - t_start

                # 合并结果
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Query task failed: {result}")
                        # 继续处理其他结果，不中断
                    elif result:
                        all_segments.extend(result)

                # 去重并按 position 排序
                unique_segments = {seg["id"]: seg for seg in all_segments}.values()
                all_segments = sorted(unique_segments, key=lambda x: x.get("position", 0))
                logger.info(
                    f"Optimized query completed: {len(all_segments)} segments "
                    f"from {len(merged_intervals)} intervals via {len(query_tasks)} queries "
                    f"in {t_elapsed:.2f}s (parallel, cache_ttl={cache_ttl}s)"
                )

            else:
                # 未指定 required_positions，使用分页获取全部（兼容 get_file_content 调用）
                page = 1
                limit = 1000

                while True:
                    response = await client.query_segments(
                        document_id=dify_document_id, status="completed", params={"limit": limit, "page": page}
                    )
                    response_data = response.json()

                    if response.status_code != 200:
                        logger.warning(f"Failed to get segments (page {page}): {response_data}")
                        break

                    segments = response_data.get("data", [])
                    if not segments:
                        break

                    all_segments.extend(segments)
                    logger.debug(f"Fetched {len(segments)} segments (page {page})")

                    if response_data.get("has_more", False):
                        page += 1
                    else:
                        if len(segments) < limit:
                            break
                        page += 1

                logger.info(f"Fetched {len(all_segments)} segments in {page} page(s)")

            # 构建返回结果
            doc_chunks = []
            for idx, segment in enumerate(all_segments):
                doc_chunks.append(
                    {
                        "id": segment.get("id", ""),
                        "content": segment.get("content", ""),
                        "chunk_order_index": idx,
                        "position": segment.get("position"),
                    }
                )

            # 优化1：存入缓存
            if required_positions and cache_ttl > 0:
                import time

                self._segments_cache[cache_key] = (doc_chunks, time.time())
                logger.debug(f"Cached {len(doc_chunks)} segments for document {dify_document_id} (TTL={cache_ttl}s)")

            return doc_chunks

        except Exception as e:
            logger.error(f"Failed to get file content from Dify: {e}")
            return []

    async def get_file_content(self, db_id: str, file_id: str) -> dict:
        """
        获取文件内容信息（支持云端原生文档）

        Args:
            db_id: 数据库ID
            file_id: 文件ID或Dify文档ID

        Returns:
            文件内容信息
        """
        # 使用具备 Cloud Fallback 的方法获取元数据
        info = await self.get_file_basic_info(db_id, file_id)
        file_meta = info["meta"]
        content_info = {"lines": []}

        # 获取 Dify document_id
        dify_document_id = file_meta.get("dify_document_id")
        if not dify_document_id:
            # 重启服务后，dify_document_id 存储在 processing_params 中
            dify_document_id = file_meta.get("processing_params", {}).get("dify_document_id")

        if dify_document_id:
            # 复用新方法获取分片
            doc_chunks = await self._fetch_sorted_segments(db_id, dify_document_id)
            content_info["lines"] = doc_chunks

            # 专家设计：如果此时还没有 content（说明无本地缓存），用片段拼接还原
            if not content_info.get("content") and doc_chunks:
                all_text_fragments = [c["content"] for c in doc_chunks]
                content_info["content"] = "\n\n".join(all_text_fragments)
                logger.info(f"Reconstructed content from {len(all_text_fragments)} segments for {file_id}")

        # Try to read markdown content if available (this will overwrite reconstructed content if exists)
        if file_meta.get("markdown_file"):
            try:
                content = await self._read_markdown_from_minio(file_meta["markdown_file"])
                content_info["content"] = content
            except Exception as e:
                logger.error(f"Failed to read markdown file for {file_id}: {e}")

        return content_info

    async def get_file_info(self, db_id: str, file_id: str) -> dict:
        """获取文件完整信息（支持基本信息 Cloud Fallback + 内容拼接）"""
        # 不再直接检查 self.files_meta，交给 get_file_basic_info 处理回退逻辑
        try:
            # 合并基本信息和内容信息
            basic_info = await self.get_file_basic_info(db_id, file_id)
            content_info = await self.get_file_content(db_id, file_id)

            return {**basic_info, **content_info}
        except Exception as e:
            logger.error(f"Failed to get complete file info for {file_id}: {e}")
            raise

    def get_database_info(self, db_id: str) -> dict | None:
        """
        获取数据库基本信息（不包含文件列表）

        Dify 知识库的文件由云端 API 管理，不在此处检索。

        Args:
            db_id: 数据库ID

        Returns:
            数据库信息或None
        """
        if db_id not in self.databases_meta:
            return None

        meta = self.databases_meta[db_id].copy()
        meta["db_id"] = db_id
        meta["files"] = {}
        meta["row_count"] = 0
        meta["status"] = "已连接"
        return meta

    def get_query_params_config(self, db_id: str, **kwargs) -> dict:
        """获取 Dify 知识库的查询参数配置"""
        options = [
            # Dify 检索配置（分组）
            {
                "type": "group",
                "label": "🔍 Dify 检索配置",
                "collapsed": False,
                "description": "配置 Dify 底层检索参数",
                "options": [
                    {
                        "key": "recall_top_k",
                        "label": "Dify召回数",
                        "type": "number",
                        "default": 20,
                        "min": 1,
                        "max": 100,
                        "description": "Dify召回数",
                    },
                    {
                        "key": "similarity_threshold",
                        "label": "相似度阈值",
                        "type": "number",
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.1,
                        "description": "过滤相似度低于此值的结果",
                    },
                    {
                        "key": "search_method",
                        "label": "搜索方法",
                        "type": "select",
                        "default": "semantic_search",
                        "options": [
                            {"value": "semantic_search", "label": "语义搜索", "description": "基于向量的语义搜索"},
                            {"value": "full_text_search", "label": "全文搜索", "description": "基于关键词的全文搜索"},
                            {"value": "hybrid_search", "label": "混合搜索", "description": "语义搜索+全文搜索"},
                        ],
                        "description": "Dify 搜索方法",
                    },
                    {
                        "key": "use_reranker",
                        "label": "启用 Dify 重排序",
                        "type": "boolean",
                        "default": False,
                        "description": "是否使用 Dify 的重排序模型",
                    },
                ],
            },
            # 高级优化参数（分组）
            {
                "type": "group",
                "label": "⚙️ 高级优化参数",
                "collapsed": True,  # 默认折叠
                "description": "调整这些参数可以优化查询性能和上下文扩展，普通用户建议使用默认值",
                "options": [
                    {
                        "key": "context_size",
                        "label": "上下文扩展",
                        "type": "number",
                        "default": 0,
                        "min": 0,
                        "max": 10,
                        "step": 1,
                        "description": "自动补充前后 n 个相邻分片（0 表示禁用）。启用后可能增加查询时间。推荐值：0-3",
                    },
                    {
                        "key": "cache_ttl",
                        "label": "缓存有效期（秒）",
                        "type": "number",
                        "default": 300,
                        "min": 0,
                        "max": 3600,
                        "step": 60,
                        "description": "查询结果缓存时间，0 表示禁用缓存。推荐值：300（5分钟）",
                    },
                    {
                        "key": "max_retries",
                        "label": "最大重试次数",
                        "type": "number",
                        "default": 3,
                        "min": 1,
                        "max": 5,
                        "step": 1,
                        "description": "API 请求失败时的重试次数。推荐值：3",
                    },
                    {
                        "key": "merge_threshold",
                        "label": "区间合并阈值",
                        "type": "number",
                        "default": 10,
                        "min": 0,
                        "max": 50,
                        "step": 1,
                        "description": "相邻区间间隔小于此值时自动合并（减少查询次数）。推荐值：10",
                    },
                    {
                        "key": "min_page_size",
                        "label": "最小页大小",
                        "type": "number",
                        "default": 20,
                        "min": 10,
                        "max": 100,
                        "step": 5,
                        "description": "每次查询最少获取的分片数。推荐值：20",
                    },
                    {
                        "key": "max_page_size",
                        "label": "最大页大小",
                        "type": "number",
                        "default": 500,
                        "min": 100,
                        "max": 1000,
                        "step": 50,
                        "description": "每次查询最多获取的分片数。网络慢时可适当调大。推荐值：500",
                    },
                    {
                        "key": "use_local_reranker",
                        "label": "启用本地重排序",
                        "type": "boolean",
                        "default": False,
                        "description": "对上下文扩展后的结果进行二次重排序（避免无关分块）",
                    },
                    {
                        "key": "local_reranker_model",
                        "label": "本地重排序模型",
                        "type": "select",
                        "default": "",
                        "options": [
                            {"label": info.name, "value": model_id}
                            for model_id, info in kwargs.get("reranker_names", {}).items()
                        ],
                        "description": "选择用于重排序的模型（需要在 config 中配置 API Key）",
                    },
                ],
            },
        ]

        return {"type": "dify", "options": options}

    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """清理资源"""
        for client in self.clients.values():
            await client.aclose()

    def __del__(self):
        """清理资源"""
        try:
            if hasattr(self, "clients"):
                # 注意：同步析构函数中无法调用异步方法
                # 需要确保在使用完后调用 aclose() 或使用 async with
                pass
        except Exception:
            pass
