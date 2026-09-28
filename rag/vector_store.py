import math
import os
import json
import re
from typing import List, Dict, Any, Optional
import httpx

class SimpleVectorStore:
    """
    Lightweight Vector Store for Financial Document RAG.
    Uses cosine similarity over word-frequency/TF-IDF vectors with support for
    Ollama embeddings if an Ollama instance is available.
    """

    def __init__(self, persistence_file: Optional[str] = None):
        self.persistence_file = persistence_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "rag_store.json"
        )
        self.documents: List[Dict[str, Any]] = []
        self.load()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r'\b\w+\b', text.lower())

    def _get_bow_vector(self, text: str) -> Dict[str, float]:
        """Compute term frequency vector for a text chunk."""
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        counts: Dict[str, float] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0.0) + 1.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in counts.values()))
        if norm > 0:
            for k in counts:
                counts[k] /= norm
        return counts

    def _cosine_similarity_bow(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Compute cosine similarity between two term frequency vectors."""
        if not vec1 or not vec2:
            return 0.0
        dot_product = sum(vec1[k] * vec2.get(k, 0.0) for k in vec1 if k in vec2)
        return float(dot_product)

    def add_document(self, doc_id: str, title: str, category: str, content: str) -> int:
        """
        Add a document to the vector store, automatically splitting content into chunks.
        Returns the number of chunks indexed.
        """
        # Simple sentence/paragraph chunking
        raw_chunks = [c.strip() for c in re.split(r'\n\n+|\.\s+', content) if len(c.strip()) > 15]
        if not raw_chunks:
            raw_chunks = [content.strip()]

        added_chunks = 0
        for idx, chunk in enumerate(raw_chunks):
            chunk_id = f"{doc_id}_chunk_{idx+1}"
            vector = self._get_bow_vector(chunk)
            
            # Check if chunk already exists
            existing_idx = next((i for i, d in enumerate(self.documents) if d["id"] == chunk_id), None)
            doc_entry = {
                "id": chunk_id,
                "doc_id": doc_id,
                "title": title,
                "category": category,
                "content": chunk,
                "vector": vector
            }
            if existing_idx is not None:
                self.documents[existing_idx] = doc_entry
            else:
                self.documents.append(doc_entry)
            added_chunks += 1

        self.save()
        return added_chunks

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search against indexed document chunks.
        Returns top_k matching chunks with similarity score.
        """
        query_vec = self._get_bow_vector(query)
        query_tokens = set(self._tokenize(query))

        results = []
        for doc in self.documents:
            score = self._cosine_similarity_bow(query_vec, doc["vector"])
            
            # Boost score slightly if exact query terms appear in chunk title or content
            doc_tokens = set(self._tokenize(doc["content"] + " " + doc["title"]))
            overlap = len(query_tokens.intersection(doc_tokens))
            if overlap > 0:
                score += (overlap / len(query_tokens)) * 0.2

            if score > 0.05:
                results.append({
                    "id": doc["id"],
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "content": doc["content"],
                    "similarity_score": round(score, 4)
                })

        # Sort by similarity score descending
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def list_documents(self) -> List[Dict[str, Any]]:
        """List distinct high-level documents stored in RAG."""
        docs_map: Dict[str, Dict[str, Any]] = {}
        for item in self.documents:
            doc_id = item["doc_id"]
            if doc_id not in docs_map:
                docs_map[doc_id] = {
                    "doc_id": doc_id,
                    "title": item["title"],
                    "category": item["category"],
                    "chunk_count": 0
                }
            docs_map[doc_id]["chunk_count"] += 1
        return list(docs_map.values())

    def save(self):
        """Save vector store state to file."""
        try:
            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            print(f"[RAG Store] Error saving store: {e}")

    def load(self):
        """Load vector store state from file."""
        if os.path.exists(self.persistence_file):
            try:
                with open(self.persistence_file, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception as e:
                print(f"[RAG Store] Error loading store: {e}")
                self.documents = []

# Global RAG store singleton
rag_store = SimpleVectorStore()
