from typing import Dict, Any, Optional
from rag.vector_store import rag_store
from rag.seed_docs import seed_financial_documents

def execute_search_documents(
    query: str,
    top_k: Optional[int] = 3
) -> Dict[str, Any]:
    """
    Search financial documents, PDF statements, tax rules, receipts, and policy terms using RAG vector search.
    """
    if not query or not isinstance(query, str):
        return {
            "success": False,
            "error": "INVALID_ARGUMENT",
            "message": "Query must be a non-empty string."
        }

    # Ensure vector store is seeded if empty
    if not rag_store.documents:
        seed_financial_documents()

    k_val = top_k if (isinstance(top_k, int) and top_k > 0) else 3
    results = rag_store.search(query=query, top_k=k_val)

    return {
        "success": True,
        "query": query,
        "top_k": k_val,
        "matches_found": len(results),
        "results": results
    }
