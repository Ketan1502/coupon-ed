# stubs: wire Vertex Embeddings + Vector Search SDK calls here
import os


def embed_text(text: str):
# TODO: call Vertex Embeddings (TextEmbedding-gecko or chosen model)
# return a list[float]
return [0.0]*1536


def upsert_vector(object_id: str, vector: list, metadata: dict):
# TODO: upsert into Vertex AI Vector Search / Matching Engine
return True


def vector_search(q_vector: list, namespace: str = None, top_k: int = 5):
# TODO: perform vector search. For now return empty
return []