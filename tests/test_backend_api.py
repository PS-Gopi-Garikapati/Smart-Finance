import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from database.seed_data import seed_database
from rag.seed_docs import seed_financial_documents

@pytest.fixture(autouse=True)
def setup_backend_data():
    seed_database()
    seed_financial_documents()

@pytest.mark.asyncio
async def test_backend_ask_valid_question():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ask", json={"question": "Did I exceed my food budget?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "grounding_status" in data
        assert data["grounding_status"] == "VERIFIED"
        assert len(data["tools_used"]) > 0

@pytest.mark.asyncio
async def test_backend_ask_empty_question():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ask", json={"question": ""})
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "cannot be empty" in data["detail"].lower()

@pytest.mark.asyncio
async def test_backend_ask_ambiguous_question():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/ask", json={"question": "Did I exceed my budget?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "specify" in data["answer"].lower() or "clarif" in data["answer"].lower() or "category" in data["answer"].lower()

@pytest.mark.asyncio
async def test_backend_documents_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List documents
        list_resp = await client.get("/api/documents")
        assert list_resp.status_code == 200
        docs = list_resp.json().get("documents", [])
        assert len(docs) > 0

        # 2. Add new document
        new_doc = {
            "doc_id": "test_lease_agreement",
            "title": "Apartment Lease Agreement 2026",
            "category": "Housing",
            "content": "Monthly rent is $2,200 due on the 1st of each month. Late fee of $75 applies after 5 days."
        }
        add_resp = await client.post("/api/documents", json=new_doc)
        assert add_resp.status_code == 200
        assert add_resp.json()["chunks_indexed"] > 0

        # 3. Search document
        search_resp = await client.post("/api/documents/search", json={"query": "rent late fee", "top_k": 2})
        assert search_resp.status_code == 200
        results = search_resp.json()["results"]
        assert len(results) > 0
        assert "75" in results[0]["content"] or "2,200" in results[0]["content"]
