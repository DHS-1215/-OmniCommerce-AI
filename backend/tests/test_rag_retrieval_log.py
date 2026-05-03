from __future__ import annotations

from uuid import uuid4

from app.models.rag import RagRetrievalLog


def test_rag_retrieval_log_model_can_be_constructed() -> None:
    tenant_id = uuid4()
    chunk_id = uuid4()
    document_id = uuid4()

    log = RagRetrievalLog(
        tenant_id=tenant_id,
        user_id=None,
        request_id="req_test",
        query="七天无理由退货",
        retrieval_mode="hybrid_opensearch",
        top_k=5,
        result_count=1,
        retrieved_chunk_ids=[str(chunk_id)],
        retrieved_document_ids=[str(document_id)],
        vector_score=1.0,
        keyword_score=0.8,
        final_score=0.93,
        scores_json=[
            {
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "vector_score": 1.0,
                "keyword_score": 0.8,
                "final_score": 0.93,
            }
        ],
        latency_ms=42,
        metadata_json={
            "source": "search",
            "retriever": "HybridRetriever",
            "keyword_store": "OpenSearchKeywordStore",
            "vector_store": "QdrantVectorStore",
        },
    )

    assert log.tenant_id == tenant_id
    assert log.request_id == "req_test"
    assert log.query == "七天无理由退货"
    assert log.retrieval_mode == "hybrid_opensearch"
    assert log.result_count == 1
    assert log.retrieved_chunk_ids == [str(chunk_id)]
    assert log.scores_json[0]["keyword_score"] == 0.8
    assert log.metadata_json["keyword_store"] == "OpenSearchKeywordStore"