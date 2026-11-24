"""RAG Knowledge Base retrieval tool for The Investigator Agent."""

from typing import Any, Dict, Optional
from app.core.logging import logger


def search_insurance_documents(
    query: str,
    category: Optional[str] = None,
    policy_type: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Search the Insurance Knowledge Base (uploaded PDFs) for policy clauses, exclusions,
    claim guidelines, terms and conditions, underwriting guidelines, or operational procedures.

    Args:
        query: Natural-language question or search query (e.g., "accidental damage coverage motor policy").
        category: Optional category filter. Allowed values:
            - "Insurance Policy Documents"
            - "Claim Guidelines"
            - "Insurance Terms and Conditions"
            - "Underwriting Guidelines"
            - "Insurance Operational Procedures"
        policy_type: Optional policy type filter (e.g., "AUTO", "HEALTH", "LIFE", "PROPERTY").
            Note: Filtering by policy_type does not prove a specific customer's policy uses
            that document; verify customer policy and document records first.
        top_k: Maximum number of relevant passages to retrieve (default 5, max 10).

    Returns:
        Dictionary with retrieved passages, document_id, document_name, page_number,
        relevant_excerpt, and similarity_score, or a clear no-results message.
    """
    try:
        from app.rag.rag_service import rag_service

        bounded_k = max(1, min(int(top_k or 5), 10))
        response = rag_service.search_documents(
            query=query,
            category=category,
            policy_type=policy_type,
            top_k=bounded_k,
        )
        if not response.passages:
            return {
                "query": query,
                "category_filter": category,
                "policy_type_filter": policy_type,
                "total_results": 0,
                "passages": [],
                "message": (
                    "No relevant passages found in the Insurance Knowledge Base for this query. "
                    "Do not assume or invent policy terms; inform the employee if relevant PDFs "
                    "have not been uploaded or indexed."
                ),
            }

        return {
            "query": query,
            "category_filter": category,
            "policy_type_filter": policy_type,
            "total_results": response.total_results,
            "passages": [
                {
                    "document_id": p.document_id,
                    "document_name": p.document_name,
                    "category": p.category,
                    "policy_type": p.policy_type,
                    "page_number": p.page_number,
                    "relevant_excerpt": p.relevant_excerpt,
                    "similarity_score": p.similarity_score,
                }
                for p in response.passages
            ],
        }
    except Exception as e:
        logger.error(f"search_insurance_documents tool failed: {e}")
        return {
            "query": query,
            "category_filter": category,
            "policy_type_filter": policy_type,
            "total_results": 0,
            "passages": [],
            "error": f"Knowledge base retrieval unavailable: {str(e)}",
        }
