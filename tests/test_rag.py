import pytest
from rag.vector_store import SimpleVectorStore, rag_store
from rag.seed_docs import seed_financial_documents
from mcp_server.tools.documents import execute_search_documents
from agent.agent_loop import GoalBasedFinanceAgent

@pytest.fixture(autouse=True)
def setup_rag():
    seed_financial_documents()

def test_vector_store_add_and_search(tmp_path):
    store_file = str(tmp_path / "test_rag_store.json")
    store = SimpleVectorStore(persistence_file=store_file)
    store.documents = []
    chunks = store.add_document(
        doc_id="test_doc_1",
        title="Insurance Policy Guide",
        category="Insurance",
        content="Health insurance claims are 100% covered for preventative visits up to $500 per year."
    )
    assert chunks > 0
    results = store.search(query="health insurance covered visits", top_k=2)
    assert len(results) > 0
    assert results[0]["doc_id"] == "test_doc_1"
    assert "500" in results[0]["content"]

def test_vector_store_tfidf_idf_weighting(tmp_path):
    store_file = str(tmp_path / "test_rag_idf.json")
    store = SimpleVectorStore(persistence_file=store_file)
    store.documents = []
    
    # Doc 1 has common word 'expense' and rare word 'crypto'
    store.add_document("doc1", "Crypto Policy", "Crypto", "crypto blockchain transactions are expense.")
    # Doc 2 and 3 also have 'expense', but do not have 'crypto'
    store.add_document("doc2", "General Expense", "Expense", "travel flight hotel expense reimbursement.")
    store.add_document("doc3", "Office Expense", "Expense", "office desk chair paper expense supplies.")
    
    # Verify IDF weights: rare word 'crypto' must have strictly higher IDF weight than common word 'expense'
    assert "crypto" in store.idf_weights
    assert "expense" in store.idf_weights
    assert store.idf_weights["crypto"] > store.idf_weights["expense"]
    
    # In doc 1 vector, crypto should have higher weight than expense even though both occur once
    doc1_vec = store.documents[0]["vector"]
    assert doc1_vec["crypto"] > doc1_vec["expense"]


def test_mcp_tool_execute_search_documents():
    res = execute_search_documents(query="tax deduction home office internet", top_k=3)
    assert res["success"] is True
    assert res["matches_found"] > 0
    top_match = res["results"][0]
    assert "Tax" in top_match["category"] or "tax" in top_match["content"].lower()

def test_mcp_tool_search_documents_invalid_arg():
    res = execute_search_documents(query="", top_k=3)
    assert res["success"] is False
    assert res["error"] == "INVALID_ARGUMENT"

@pytest.mark.asyncio
async def test_agent_loop_rag_document_question():
    agent = GoalBasedFinanceAgent()
    resp = await agent.run("What is the tax deduction policy for home office internet in 2026?")
    assert resp.answer is not None
    assert "search_documents" in resp.tools_used
    assert "tax" in resp.answer.lower() or "1,500" in resp.answer or "deduction" in resp.answer.lower()
