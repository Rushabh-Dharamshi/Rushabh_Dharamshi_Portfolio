def test_rag_blueprint_endpoints(client, app):
    class FakeRagService:
        def status(self):
            return {
                "available": True,
                "collection_name": "monetra-finance-knowledge",
                "indexed_at": "2026-04-15T09:00:00Z",
                "document_count": 12,
                "chunk_count": 36,
                "signature": "sig",
            }

        def reindex(self, force=False):
            return {
                "available": True,
                "collection_name": "monetra-finance-knowledge",
                "indexed_at": "2026-04-15T09:05:00Z",
                "document_count": 13,
                "chunk_count": 39,
                "signature": "sig-2",
                "reindexed": force,
            }

        def answer_question(self, question):
            assert question == "What changed this month?"
            return {
                "question": question,
                "answer": "Housing remains the largest cost center.",
                "confidence": "high",
                "follow_up_questions": ["Which reminders are due next?"],
                "sources": [
                    {
                        "source_label": "Dashboard March 2026",
                        "doc_type": "dashboard",
                        "document_id": "dashboard::2026-03",
                        "excerpt": "Monthly budget is GBP 1050.",
                        "score": 0.95,
                        "metadata": {},
                    }
                ],
                "generated_at": "2026-04-15T09:10:00Z",
            }

    app.extensions["services"]["rag_service"] = FakeRagService()

    status = client.get("/api/rag/status")
    reindex = client.post("/api/rag/reindex", json={"force": True})
    query = client.post("/api/rag/query", json={"question": "What changed this month?"})

    assert status.status_code == 200
    assert status.get_json()["data"]["chunk_count"] == 36
    assert reindex.get_json()["data"]["reindexed"] is True
    assert query.get_json()["data"]["confidence"] == "high"
