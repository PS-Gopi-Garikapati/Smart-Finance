from rag.vector_store import rag_store

SEED_DOCUMENTS = [
    {
        "doc_id": "doc_tax_guide_2026",
        "title": "2026 Personal Income Tax & Deduction Policy",
        "category": "Tax Policy",
        "content": (
            "Under the 2026 Income Tax rules, individuals can claim tax deductions for work-from-home expenses, "
            "up to $1,500 per year for high-speed internet, ergonomic equipment, and electricity usage. "
            "Medical expenses exceeding $2,000 per year are eligible for a 15% tax rebate when supported by itemized receipts. "
            "Educational courses and professional certifications required for career advancement are 100% tax deductible up to $3,000."
        )
    },
    {
        "doc_id": "doc_credit_card_terms",
        "title": "Smart Card Rewards & Fee Policy",
        "category": "Credit Card Terms",
        "content": (
            "The Smart Rewards Credit Card has an annual membership fee of $99, waived if total annual spending exceeds $10,000. "
            "Grocery and Supermarket purchases earn 3% cashback. Dining and restaurant expenses earn 2% cashback. "
            "Foreign transaction fees are 0% for international purchases. Late payment charges are $35 per billing cycle."
        )
    },
    {
        "doc_id": "doc_receipt_apple_store",
        "title": "Apple Store Itemized Purchase Receipt - Sept 2026",
        "category": "Receipts",
        "content": (
            "Apple Store Official Receipt #AP-99482. Date: September 12, 2026. "
            "Purchased Items: 1x MacBook Pro 16-inch M3 Max ($2,499.00), 1x USB-C Multi-Port Adapter ($69.00), "
            "1x AppleCare+ 3-Year Protection Plan ($399.00). Total paid: $2,967.00 via Smart Rewards Credit Card. "
            "Warranty coverage valid through September 2029."
        )
    },
    {
        "doc_id": "doc_company_reimbursement",
        "title": "Corporate Travel & Expense Reimbursement Limits",
        "category": "Company Policy",
        "content": (
            "Employees on business travel can claim up to $75 per day for meals without submitting individual itemized receipts. "
            "Airfare must be booked in Economy Class at least 14 days in advance. Uber/Taxi rides to and from airports are 100% reimbursable. "
            "All expense reimbursement claims must be submitted within 30 days of expense incurrence."
        )
    }
]

def seed_financial_documents():
    """Seed sample financial documents into the RAG vector store."""
    total_chunks = 0
    for doc in SEED_DOCUMENTS:
        chunks = rag_store.add_document(
            doc_id=doc["doc_id"],
            title=doc["title"],
            category=doc["category"],
            content=doc["content"]
        )
        total_chunks += chunks
    print(f"[RAG Seed] Successfully seeded {len(SEED_DOCUMENTS)} documents ({total_chunks} chunks indexed).")

if __name__ == "__main__":
    seed_financial_documents()
