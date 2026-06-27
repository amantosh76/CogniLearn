import os
import time
import hashlib
from typing import List, Dict, Optional
import google.generativeai as genai
import chromadb
from chromadb.config import Settings
from config import GEMINI_API_KEY, EMBEDDING_MODEL, CHROMA_DB_PATH

class EmbeddingEngine:
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = EMBEDDING_MODEL
        self._cache = {}

    def embed_text(self, text: str) -> List[float]:
        # Single text embedding
        key = hashlib.md5(text.encode()).hexdigest()
        if key not in self._cache:
            self._cache[key] = self._embed_with_retry([text], "retrieval_document")[0]
        return self._cache[key]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Batch text embeddings
        results = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            results.extend(self._embed_with_retry(batch, "retrieval_document"))
            if i + batch_size < len(texts):
                time.sleep(0.5)
        return results

    def embed_query(self, query: str) -> List[float]:
        # Query embedding API
        return self._embed_with_retry([query], "retrieval_query")[0]

    def _embed_with_retry(self, texts: List[str], task_type: str, retries: int = 3) -> List[List[float]]:
        # Embed with retries
        for attempt in range(retries):
            try:
                res = genai.embed_content(model=self.model, content=texts, task_type=task_type)
                return res['embedding'] if isinstance(res['embedding'][0], list) else [res['embedding']]
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2.0 * (attempt + 1))
                else:
                    raise

class VectorStore:
    def __init__(self):
        # Init Chroma database
        self.client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="cognilearn_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, ids: List[str], texts: List[str], embeddings: List[List[float]], metadatas: List[Dict]):
        # Add chunks database
        for i in range(0, len(ids), 100):
            end = min(i + 100, len(ids))
            self.collection.add(
                ids=ids[i:end],
                documents=texts[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end]
            )

    def query(self, query_embedding: List[float], top_k: int = 10, filter_dict: Optional[Dict] = None) -> List[Dict]:
        # Query matching vectors
        count = self.collection.count()
        if count == 0:
            return []
        params = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, count),
            "include": ["documents", "metadatas", "distances"]
        }
        if filter_dict:
            params["where"] = filter_dict
        try:
            res = self.collection.query(**params)
            if not res or not res["ids"] or not res["ids"][0]:
                return []
            return [{
                "id": res["ids"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i],
                "score": 1.0 - res["distances"][0][i]
            } for i in range(len(res["ids"][0]))]
        except Exception:
            return []

    def delete_document(self, doc_id: str):
        # Delete document record
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

    def get_all_documents(self) -> List[Dict]:
        # Fetch metadata list
        try:
            data = self.collection.get(include=["metadatas"])
            if not data or not data["metadatas"]:
                return []
            docs = {}
            for m in data["metadatas"]:
                doc_id = m.get("doc_id", "unknown")
                if doc_id not in docs:
                    docs[doc_id] = {
                        "doc_id": doc_id,
                        "filename": m.get("filename", "unknown"),
                        "num_chunks": 0,
                        "total_chars": 0,
                        "file_type": m.get("file_type", "unknown")
                    }
                docs[doc_id]["num_chunks"] += 1
                docs[doc_id]["total_chars"] += int(m.get("chunk_char_count", 0))
            return list(docs.values())
        except Exception:
            return []

    def get_all_texts_and_ids(self) -> tuple:
        # Fetch document texts
        try:
            data = self.collection.get(include=["documents", "metadatas"])
            return data["documents"] or [], data["ids"] or [], data["metadatas"] or []
        except Exception:
            return [], [], []

    def count(self) -> int:
        # Count total vectors
        try:
            return self.collection.count()
        except Exception:
            return 0
