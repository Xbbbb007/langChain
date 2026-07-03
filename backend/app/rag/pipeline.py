import json
from typing import List, Dict, Any, Generator
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from backend.app.config import settings

class RAGPipeline:
    """
    RAG (检索增强生成) 核心管道处理类。
    负责管理：
    1. 阿里通义千问云端 Embedding 模型 (`text-embedding-v3`) 客户端的构建。
    2. 本地 Chroma 向量数据库连接的建立与生命周期维护。
    3. 通义千问大语言模型客户端 (`qwen-plus`) 的流式传输对接。
    """
    def __init__(self):
        # Initialize embeddings with DashScope compatible mode
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-v3",
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.DASHSCOPE_BASE_URL,
            check_embedding_ctx_length=False
        )
        # Initialize Chroma Vector Store
        self.vector_db = Chroma(
            persist_directory=settings.CHROMA_DB_DIR,
            embedding_function=self.embeddings
        )
        # Initialize LLM with DashScope compatible mode
        self.llm = ChatOpenAI(
            model="qwen-plus",
            openai_api_key=settings.DASHSCOPE_API_KEY,
            openai_api_base=settings.DASHSCOPE_BASE_URL,
            streaming=True,
            temperature=0.2  # low temperature for RAG to remain factual
        )

    def add_documents(self, documents: List[Any]):
        """Add LangChain documents to vector database."""
        self.vector_db.add_documents(documents)

    def delete_document(self, document_id: str):
        """Delete all chunks belonging to a document_id."""
        try:
            # Query IDs first
            res = self.vector_db.get(where={"document_id": document_id})
            ids = res.get("ids", [])
            if ids:
                self.vector_db.delete(ids=ids)
                return True
        except Exception as e:
            print(f"Error deleting from vector DB: {e}")
        return False

    def retrieve_context(self, query: str, k: int = 5, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks with scores."""
        # Chroma similarity_search_with_relevance_scores returns (doc, score)
        # DashScope embeddings + Chroma score is usually similarity metric (higher is better, or distance)
        results = self.vector_db.similarity_search_with_relevance_scores(query, k=k)
        
        retrieved_sources = []
        for doc, score in results:
            # Check threshold (adjust if metric is distance vs cosine similarity)
            # In LangChain Chroma, relevance score is normalized to [0, 1] (higher = more similar)
            if score >= score_threshold:
                retrieved_sources.append({
                    "content": doc.page_content,
                    "source_name": doc.metadata.get("source_name", "未知文件"),
                    "document_id": doc.metadata.get("document_id", ""),
                    "chunk_id": doc.metadata.get("chunk_id", 0),
                    "score": float(score)
                })
        return retrieved_sources

    def generate_rag_stream(
        self, 
        query: str, 
        chat_history: List[Dict[str, str]], 
        k: int = 5, 
        score_threshold: float = 0.3
    ) -> Generator[str, None, None]:
        """
        Generate streaming RAG response via SSE.
        Yields JSON strings:
        - {"type": "sources", "sources": [...]} (sent first)
        - {"type": "text", "content": "..."} (sent in chunks)
        - {"type": "done"} (sent at the end)
        """
        # 1. Retrieve relevant chunks
        sources = self.retrieve_context(query, k=k, score_threshold=score_threshold)
        
        # Format sources for sending to client
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

        # 2. Build context text
        if sources:
            context_str = "\n\n".join([
                f"【文件来源: {s['source_name']} (得分: {s['score']:.2f})】\n{s['content']}"
                for s in sources
            ])
        else:
            context_str = "未找到相关的商品知识库参考信息。"

        # 3. Build Prompt
        system_prompt = (
            "你是一个专业的电商平台智能客服助手，专门负责解答关于售卖商品的问题。\n"
            "请严格根据以下【参考知识库内容】来回答用户的问题。如果回答中引用了特定内容，请在回答中客观陈述。\n"
            "如果【参考知识库内容】中没有相关信息，或者无法从中得出答案，请礼貌地回答：'对不起，在当前商品知识库中没有找到相关信息。'\n"
            "切记：不要胡编乱造商品参数、价格或优惠活动，所有回答必须基于提供的知识库内容。\n\n"
            f"【参考知识库内容】：\n{context_str}"
        )

        # 4. Build Messages including history
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add history (limit to last 6 messages for token efficiency)
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": query})


        
        # Determine whether to enable thinking based on query complexity and RAG context
        enable_thinking = False

        # 5. Call OpenAI client and stream response (supporting thinking process)
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url=settings.DASHSCOPE_CHAT_BASE_URL
            )
            
            completion = client.chat.completions.create(
                model=settings.DASHSCOPE_CHAT_MODEL,
                messages=messages,
                extra_body={"enable_thinking": enable_thinking},
                stream=True
            )
            
            full_response = ""
            
            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                # Output thinking process to the backend console for debugging/logging,
                # but do NOT stream it to the client.
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    print(reasoning, end="", flush=True)
                
                # Stream only the final answer content to the client
                content = getattr(delta, "content", None)
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
            
            # Send done with full content to save in database
            yield f"data: {json.dumps({'type': 'done', 'full_content': full_response})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'生成回答时发生错误: {str(e)}'})}\n\n"

# Lazy-loaded singleton
_rag_pipeline = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
