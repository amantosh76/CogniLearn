from typing import List, Dict

class HybridSearch:
    def __init__(self, alpha: float = 0.7, rrf_k: int = 60):
        # Init weight constants
        self.alpha = alpha
        self.rrf_k = rrf_k

    def fuse(self, semantic_results: List[Dict], keyword_results: List[Dict], top_k: int = 10) -> List[Dict]:
        # Fuses retrieval results
        scores = {}
        result_map = {}

        # Semantic score calculation
        for rank, res in enumerate(semantic_results):
            rid = res["id"]
            scores[rid] = scores.get(rid, 0.0) + self.alpha / (self.rrf_k + rank + 1)
            result_map[rid] = res

        # Lexical score calculation
        for rank, res in enumerate(keyword_results):
            rid = res["id"]
            scores[rid] = scores.get(rid, 0.0) + (1.0 - self.alpha) / (self.rrf_k + rank + 1)
            if rid not in result_map:
                result_map[rid] = res

        # Sort combined results
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        
        fused = []
        for rid in sorted_ids:
            item = result_map[rid].copy()
            item["fused_score"] = scores[rid]
            fused.append(item)
        return fused
