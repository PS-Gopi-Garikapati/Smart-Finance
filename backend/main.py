import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add root directory to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import settings
from database.seed_data import seed_database
from database.database import DEFAULT_DB_PATH
from agent.agent_loop import GoalBasedFinanceAgent
from agent.schemas import AgentResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("FastAPIBackend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup event initializing SQLite database and verifying seed data."""
    logger.info("Initializing Smart Finance Agent Database...")
    db_file = os.getenv("DB_PATH", DEFAULT_DB_PATH)
    if not os.path.exists(db_file) or os.path.getsize(db_file) == 0:
        seed_database(db_file)
    logger.info("Database ready.")
    yield
    logger.info("Shutting down backend server.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local web interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from rag.vector_store import rag_store
from rag.seed_docs import seed_financial_documents

class QuestionRequest(BaseModel):
    question: str

class DocumentUploadRequest(BaseModel):
    doc_id: str
    title: str
    category: str
    content: str

class SearchDocumentsRequest(BaseModel):
    query: str
    top_k: int = 3

@app.post("/api/ask", response_model=AgentResponse)
async def ask_finance_question(req: QuestionRequest):
    """
    Process natural-language financial question through the Goal-Based Agent loop.
    Returns grounded answer, tool execution trace, observations, and reflection audit.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        agent = GoalBasedFinanceAgent()
        response = await agent.run(req.question.strip())
        return response
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")

@app.get("/api/documents")
async def list_rag_documents():
    """List all financial documents currently indexed in the RAG Vector Store."""
    if not rag_store.documents:
        seed_financial_documents()
    return {"success": True, "documents": rag_store.list_documents()}

@app.post("/api/documents")
async def add_rag_document(doc: DocumentUploadRequest):
    """Add a new financial document, receipt, or policy text to the RAG Vector Store."""
    chunks = rag_store.add_document(
        doc_id=doc.doc_id,
        title=doc.title,
        category=doc.category,
        content=doc.content
    )
    return {
        "success": True,
        "message": f"Document '{doc.title}' successfully indexed into RAG store ({chunks} chunks).",
        "doc_id": doc.doc_id,
        "chunks_indexed": chunks
    }

@app.post("/api/documents/search")
async def search_rag_documents(req: SearchDocumentsRequest):
    """Perform RAG vector similarity search directly on indexed financial documents."""
    if not rag_store.documents:
        seed_financial_documents()
    results = rag_store.search(query=req.query, top_k=req.top_k)
    return {"success": True, "query": req.query, "results": results}

# Mount static frontend directory
frontend_dir = os.path.join(ROOT_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
