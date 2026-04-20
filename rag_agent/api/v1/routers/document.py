from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.document import DocumentCreate, DocumentRead, DocumentList
from services.document import DocumentService
from services.process import process_document

router = APIRouter()


@router.post("/documents", 
             response_model=DocumentRead,
             status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db)
):
    service = DocumentService(db)
    return await service.create(data)


@router.get("/documents",
            response_model=DocumentList)
async def list_documents(
    skip: int=0,
    limit: int=20,
    db: AsyncSession = Depends(get_db)
):
    service = DocumentService(db)
    total, items = await service.list(skip, limit)
    return DocumentList(total=total, items=items)


@router.get("/documents/{doc_id}",
            response_model=DocumentRead)
async def get_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = DocumentService(db)
    doc = await service.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document Not Found!"
        )
    return doc


@router.delete("/documents/{doc_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = DocumentService(db)
    doc = await service.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404,
                            detail="Document Not Found!")
    await service.delete(doc)


@router.post("/documents/{doc_id}/preprocess",
             response_model=DocumentRead)
async def trigger_process(doc_id: int,
                          db: AsyncSession=Depends(get_db)):
    service = DocumentService(db)
    doc = await service.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404,
                            detail="Document not found")
    await process_document(doc, db)
    await db.refresh(doc)
    # 新从数据库读一次，拿到最新的 status 和 chunk_count
    return doc