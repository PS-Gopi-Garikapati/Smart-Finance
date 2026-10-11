from typing import Dict, Any, Optional
from rag.vector_store import rag_store
from rag.seed_docs import seed_financial_documents
from mcp_server.tools.validators import SearchDocumentsInput, validation_error

def execute_search_documents(
    query: str,
    top_k: Optional[int] = 3
) -> Dict[str, Any]:
    """
    Search financial documents, PDF statements, tax rules, receipts, and policy terms using RAG vector search.
    """
    try:
        validated = SearchDocumentsInput(query=query, top_k=top_k if top_k is not None else 3)
    except Exception as e:
        msg = str(e)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1]
        return validation_error(msg)

    # Ensure vector store is seeded if empty
    if not rag_store.documents:
        seed_financial_documents()

    results = rag_store.search(query=validated.query, top_k=validated.top_k)

    return {
        "success": True,
        "query": validated.query,
        "top_k": validated.top_k,
        "matches_found": len(results),
        "results": results
    }
