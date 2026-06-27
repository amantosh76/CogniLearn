import re
from typing import List, Dict
from rank_bm25 import BM25Okapi

class BM25Search:
    def __init__(self):
        # Index values init
        self.index = None
        self.documents = []
        self.doc_ids = []
        self.doc_metadatas = []

    def build_index(self, texts: List[str], doc_ids: List[str], metadatas: List[Dict]):
        # Index documents list
        self.documents = texts
        self.doc_ids = doc_ids
        self.doc_metadatas = metadatas
        tokenized = [self._tokenize(d) for d in texts]
        if tokenized:
            self.index = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        # Keyword search documents
        if not self.index or not self.documents:
            return []
        tokenized_query = self._tokenize(query)
        scores = self.index.get_scores(tokenized_query)
        scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        
        max_score = max(scores) if max(scores) > 0 else 1.0
        results = []
        for idx, score in scored:
            if score > 0:
                results.append({
                    "id": self.doc_ids[idx],
                    "text": self.documents[idx],
                    "metadata": self.doc_metadatas[idx],
                    "score": score / max_score,
                })
        return results

    def _tokenize(self, text: str) -> List[str]:
        # Lexical tokenizer helper
        tokens = re.findall(r'\b\w+\b', text.lower())
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'can', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'it', 'its', 'this', 'that', 'and', 'or', 'but', 'not'}
        return [t for t in tokens if t not in stopwords and len(t) > 1]
