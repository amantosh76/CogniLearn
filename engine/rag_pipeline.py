import json
import time
import re
from typing import List, Dict, Optional, Generator
import google.generativeai as genai
from config import GEMINI_API_KEY, LLM_MODEL, TOP_K_RETRIEVAL, TOP_K_RERANK, HYBRID_ALPHA, MAX_CONTEXT_LENGTH
from engine.vector_store import EmbeddingEngine, VectorStore
from engine.lexical import BM25Search
from engine.fusion import HybridSearch
from engine.reranker import Reranker
from engine.memory import ConversationMemory

class RAGChain:
    def __init__(self):
        # Init RAG instances
        genai.configure(api_key=GEMINI_API_KEY)
        self.llm = genai.GenerativeModel(LLM_MODEL)
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore()
        self.bm25 = BM25Search()
        self.hybrid = HybridSearch(alpha=HYBRID_ALPHA)
        self.reranker = Reranker()
        self.memory = ConversationMemory()
        self._query_log = []
        self._refresh_bm25_index()

    def _refresh_bm25_index(self):
        # Rebuild lexical index
        texts, ids, metadatas = self.vector_store.get_all_texts_and_ids()
        if texts:
            self.bm25.build_index(texts, ids, metadatas)

    def add_document(self, doc_info: Dict):
        # Index document chunks
        chunks = doc_info["chunks"]
        if not chunks:
            return
        texts = [c.text for c in chunks]
        ids = [c.id for c in chunks]
        metadatas = [c.metadata for c in chunks]
        embeddings = self.embedding_engine.embed_batch(texts)
        self.vector_store.add_chunks(ids, texts, embeddings, metadatas)
        self._refresh_bm25_index()

    def delete_document(self, doc_id: str):
        # Remove document chunks
        self.vector_store.delete_document(doc_id)
        self._refresh_bm25_index()

    def query(self, question: str, session_id: str = "default") -> Dict:
        # Full RAG query
        start_time = time.time()
        query_embedding = self.embedding_engine.embed_query(question)
        semantic_results = self.vector_store.query(query_embedding, top_k=TOP_K_RETRIEVAL)
        keyword_results = self.bm25.search(question, top_k=TOP_K_RETRIEVAL)
        fused_results = self.hybrid.fuse(semantic_results, keyword_results, top_k=TOP_K_RETRIEVAL)
        reranked_results = self.reranker.rerank(question, fused_results, top_k=TOP_K_RERANK)
        context = self._build_context(reranked_results)
        history = self.memory.get_context_string(session_id)
        prompt = self._build_prompt(question, context, history)
        
        response = self.llm.generate_content(prompt)
        answer_text = response.text
        confidence = self._extract_confidence(answer_text)
        clean_answer = self._clean_answer(answer_text)

        self.memory.add_turn(session_id, "user", question)
        self.memory.add_turn(session_id, "assistant", clean_answer)
        elapsed = time.time() - start_time
        citations = self._build_citations(reranked_results)

        result = {
            "answer": clean_answer,
            "confidence": confidence,
            "citations": citations,
            "elapsed_time": round(elapsed, 2),
            "num_sources": len(citations),
        }

        self._query_log.append({
            "question": question,
            "elapsed_time": elapsed,
            "num_citations": len(citations),
            "confidence": confidence,
            "timestamp": time.time(),
        })
        return result

    def stream_query(self, question: str, session_id: str = "default") -> Generator:
        # Stream RAG query
        start_time = time.time()
        query_embedding = self.embedding_engine.embed_query(question)
        semantic_results = self.vector_store.query(query_embedding, top_k=TOP_K_RETRIEVAL)
        keyword_results = self.bm25.search(question, top_k=TOP_K_RETRIEVAL)
        fused_results = self.hybrid.fuse(semantic_results, keyword_results, top_k=TOP_K_RETRIEVAL)
        reranked_results = self.reranker.rerank(question, fused_results, top_k=TOP_K_RERANK)
        context = self._build_context(reranked_results)
        history = self.memory.get_context_string(session_id)
        prompt = self._build_prompt(question, context, history)

        citations = self._build_citations(reranked_results)
        yield json.dumps({"type": "citations", "data": citations})

        response = self.llm.generate_content(prompt, stream=True)
        full_answer = ""
        for chunk in response:
            if chunk.text:
                full_answer += chunk.text
                yield json.dumps({"type": "token", "data": chunk.text})

        clean_answer = self._clean_answer(full_answer)
        confidence = self._extract_confidence(full_answer)
        self.memory.add_turn(session_id, "user", question)
        self.memory.add_turn(session_id, "assistant", clean_answer)
        elapsed = time.time() - start_time

        self._query_log.append({
            "question": question,
            "elapsed_time": elapsed,
            "num_citations": len(citations),
            "confidence": confidence,
            "timestamp": time.time(),
        })

        yield json.dumps({
            "type": "done",
            "data": {
                "confidence": confidence,
                "elapsed_time": round(elapsed, 2),
                "num_sources": len(citations),
            }
        })

    def _build_citations(self, results: List[Dict]) -> List[Dict]:
        # Formats sources list
        citations = []
        for i, r in enumerate(results):
            citations.append({
                "index": i + 1,
                "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                "full_text": r["text"],
                "filename": r["metadata"].get("filename", "Unknown"),
                "chunk_index": r["metadata"].get("chunk_index", 0),
                "relevance_score": round(r.get("rerank_score", r.get("fused_score", r.get("score", 0))), 2),
            })
        return citations

    def _build_context(self, results: List[Dict]) -> str:
        # Formats context string
        if not results:
            return "No relevant documents found."
        parts = []
        total_chars = 0
        for i, r in enumerate(results):
            txt = f"[Source {i + 1} — {r['metadata'].get('filename', 'Unknown')}]:\n{r['text']}"
            if total_chars + len(txt) > MAX_CONTEXT_LENGTH:
                break
            parts.append(txt)
            total_chars += len(txt)
        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, question: str, context: str, history: str) -> str:
        # Prompt build helper
        hist_sec = f"\n## Previous Conversation\n{history}\n" if history else ""
        return f"""You are CogniLearn, an intelligent research assistant. Answer the user's question based ONLY on the provided context from their documents. Follow these rules strictly:

1. **Use ONLY the provided context** to answer. Do not make up information.
2. **Cite your sources** by referencing [Source N] in your answer.
3. **If the context doesn't contain enough information**, say so clearly.
4. **Be thorough but concise** — provide a complete answer without unnecessary padding.
5. At the very end of your answer, on a new line, write "CONFIDENCE: X/10" where X is your confidence in the answer (1-10).
{hist_sec}
## Context from Documents
{context}

## User Question
{question}

## Your Answer (with citations):"""

    def _extract_confidence(self, text: str) -> float:
        # Extract confidence value
        match = re.search(r'CONFIDENCE:\s*(\d+(?:\.\d+)?)\s*/\s*10', text)
        return min(10.0, max(0.0, float(match.group(1)))) if match else 7.0

    def _clean_answer(self, text: str) -> str:
        # Remove confidence suffix
        return re.sub(r'\n*CONFIDENCE:\s*\d+(?:\.\d+)?\s*/\s*10\s*$', '', text).strip()

    def get_analytics(self) -> Dict:
        # Fetch statistics summary
        if not self._query_log:
            return {
                "total_queries": 0,
                "avg_response_time": 0,
                "avg_confidence": 0,
                "avg_citations": 0,
                "recent_queries": [],
            }
        return {
            "total_queries": len(self._query_log),
            "avg_response_time": round(sum(q["elapsed_time"] for q in self._query_log) / len(self._query_log), 2),
            "avg_confidence": round(sum(q["confidence"] for q in self._query_log) / len(self._query_log), 1),
            "avg_citations": round(sum(q["num_citations"] for q in self._query_log) / len(self._query_log), 1),
            "recent_queries": [
                {"question": q["question"][:80], "time": round(q["elapsed_time"], 2), "confidence": q["confidence"]}
                for q in self._query_log[-20:]
            ],
        }
