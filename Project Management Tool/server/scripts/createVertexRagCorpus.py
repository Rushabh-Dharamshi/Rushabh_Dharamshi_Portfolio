#!/usr/bin/env python3
"""
Create a Vertex AI RAG corpus for the Project Management Tool.

Usage (Windows cmd):
  set GCP_PROJECT_ID=project-management-tool-488116
  set GCP_REGION=europe-west2
  set VERTEX_RAG_CORPUS_DISPLAY_NAME=pm-tool-corpus
  python scripts/createVertexRagCorpus.py
"""

import os
import sys

import vertexai
from vertexai import rag


def main() -> int:
    project_id = os.getenv("GCP_PROJECT_ID")
    region = os.getenv("GCP_REGION", "europe-west2")
    display_name = os.getenv("VERTEX_RAG_CORPUS_DISPLAY_NAME", "pm-tool-corpus")
    embedding_model = os.getenv(
        "VERTEX_RAG_EMBEDDING_MODEL",
        "publishers/google/models/text-embedding-005",
    )

    if not project_id:
        print("Error: Missing GCP_PROJECT_ID. Set it and retry.")
        return 1

    try:
        vertexai.init(project=project_id, location=region)

        embedding_model_config = rag.RagEmbeddingModelConfig(
            vertex_prediction_endpoint=rag.VertexPredictionEndpoint(
                publisher_model=embedding_model
            )
        )

        backend_config = rag.RagVectorDbConfig(
            rag_embedding_model_config=embedding_model_config
        )

        corpus = rag.create_corpus(
            display_name=display_name,
            backend_config=backend_config,
        )

        print("Vertex RAG corpus created successfully.")
        print(f"Corpus resource name: {corpus.name}")
        print(f"Corpus display name: {display_name}")

        corpus_id = str(corpus.name).rstrip("/").split("/")[-1]
        print(f"Corpus ID: {corpus_id}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to create corpus: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
