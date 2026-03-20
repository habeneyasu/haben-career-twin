import os
import asyncio
from typing import Dict, List

from src.pipeline.chunking import chunk_documents
from src.pipeline.embedding import embed_chunk_records, embed_texts
from src.pipeline.ingestion import ingest_documents, ingest_live_documents_async
from src.pipeline.metadata import build_document_metadata
from src.pipeline.vector_store import query_similar_chunks, upsert_embedding_records


def build_vector_index(
    use_live: bool = True,
    include_local_processed: bool = False,
    processed_dir: str = "",
    cache_ttl_seconds: int = 0,
    cache_db_path: str = "",
    dynamic_chunking: bool = True,
    chunk_size: int = 0,
    overlap: int = 0,
    embedding_model: str = "",
    embedding_batch_size: int = 0,
    use_async_ingestion: bool = False,
) -> Dict[str, int]:
    """
    End-to-end indexing pipeline:
    1) ingest docs
    2) build metadata
    3) chunk docs
    4) embed chunks
    5) upsert vectors
    """
    async_default = os.getenv("USE_ASYNC_INGESTION", "false").lower() == "true"
    resolved_async = use_async_ingestion or async_default

    if resolved_async and use_live and not include_local_processed:
        docs = asyncio.run(
            ingest_live_documents_async(
                cache_ttl_seconds=cache_ttl_seconds,
                cache_db_path=cache_db_path,
            )
        )
    else:
        docs = ingest_documents(
            use_live=use_live,
            include_local_processed=include_local_processed,
            processed_dir=processed_dir,
            cache_ttl_seconds=cache_ttl_seconds,
            cache_db_path=cache_db_path,
        )
    if not docs:
        return {
            "documents_ingested": 0,
            "chunks_created": 0,
            "vectors_upserted": 0,
        }

    chunks_created = 0
    upserted = 0
    for doc in docs:
        merged: Dict[str, str] = dict(doc)
        merged.update(build_document_metadata(doc, default_ttl_seconds=cache_ttl_seconds))

        doc_chunks = chunk_documents(
            [merged],
            chunk_size=(chunk_size or None),
            overlap=(overlap or None),
            dynamic=dynamic_chunking,
        )
        chunks_created += len(doc_chunks)

        if not doc_chunks:
            continue

        if embedding_model:
            embedded_chunks = embed_chunk_records(
                doc_chunks,
                model=embedding_model,
                batch_size=embedding_batch_size,
            )
        else:
            embedded_chunks = embed_chunk_records(
                doc_chunks,
                batch_size=embedding_batch_size,
            )

        upserted += upsert_embedding_records(embedded_chunks)

    return {
        "documents_ingested": len(docs),
        "chunks_created": chunks_created,
        "vectors_upserted": upserted,
    }


def search_similar_content(
    query: str,
    top_k: int = 0,
    embedding_model: str = "",
) -> List[Dict[str, object]]:
    """
    Query pipeline:
    1) embed query
    2) semantic search in vector store
    """
    if not query.strip():
        return []
    if embedding_model:
        vector = embed_texts([query], model=embedding_model)
    else:
        vector = embed_texts([query])
    if not vector:
        return []
    return query_similar_chunks(query_embedding=vector[0], top_k=top_k)

