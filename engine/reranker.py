import re
from typing import List, Dict
import google.generativeai as genai
from config import GEMINI_API_KEY, LLM_MODEL

class Reranker:
    def __init__(self):
        # Configure model client
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(LLM_MODEL)

    def rerank(self, query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
        # Re-rank search results
        if not results:
            return []
        if len(results) <= top_k:
            return results

        try:
            chunks_text = "".join(f"\n[Chunk {i}]: {r['text'][:300]}\n" for i, r in enumerate(results))
            prompt = f"""You are a relevance scorer. Given a query and document chunks, score EACH chunk from 0 to 10 based on how relevant it is to answering the query.

Query: {query}

Chunks:
{chunks_text}

Respond ONLY with scores in this exact format (one per line):
Chunk 0: <score>
Chunk 1: <score>"""
            
            res = self.model.generate_content(prompt)
            scores = self._parse_scores(res.text, len(results))

            for i, r in enumerate(results):
                r["rerank_score"] = scores.get(i, 5.0)

            results.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return results[:top_k]

        except Exception as e:
            print(f"⚠️ Rerank failed: {e}")
            return results[:top_k]

    def _parse_scores(self, text: str, num_chunks: int) -> Dict[int, float]:
        # Parse scores helper
        scores = {}
        for line in text.strip().split("\n"):
            match = re.search(r'Chunk\s*(\d+)\s*:\s*([\d.]+)', line)
            if match:
                idx = int(match.group(1))
                val = min(10.0, max(0.0, float(match.group(2))))
                if idx < num_chunks:
                    scores[idx] = val
        return scores
