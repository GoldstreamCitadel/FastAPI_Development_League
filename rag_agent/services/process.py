# pipeline
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, DocumentStatus
from models.chunk import Chunk
from services.chunker import split_text
from services.embedder import embed_texts
from services.vector_store import get_collection, upsert, delete

async def process_document(doc: Document,
                           db: AsyncSession) -> None:
    doc.status = DocumentStatus.processing
    await db.flush()

    try:
        texts = split_text(doc.content)
        embeddings = await embed_texts(texts)

        collection = get_collection()
        ids = [f"{doc.id}_{i}" for i in range(len(texts))]
        upsert(collection, ids=ids,
               embeddings=embeddings, documents=texts)
        
        for i, (text, vector_id) in enumerate(zip(texts, ids)):
            chunk = Chunk(
                document_id=doc.id,
                content=text,
                chunk_index=i,
                vector_id=vector_id,
            )
            db.add(chunk)

        doc.status = DocumentStatus.ready
        doc.chunk_count = len(texts)

    except Exception:
        doc.status = DocumentStatus.failed
        raise

    await db.flush()