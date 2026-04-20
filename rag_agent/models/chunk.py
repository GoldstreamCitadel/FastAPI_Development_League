# chunk ORM model
from sqlalchemy import Integer, Text, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    vector_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

"""
---                                                      
Chunk 是什么
                                                        
一个 Document 被切成多个 Chunk，
Chunk表存的是每个块的元数据，不是向量本身。
向量存在 ChromaDB里，
SQLite 只存文本内容和索引信息。
两个存储通过vector_id 关联起来。

Document (SQLite)
    ↓  1:N
Chunk (SQLite)  ←→  vector_id  ←→  ChromaDB 向量        

---

---
chunk_index 和 vector_id

chunk_index — 块在原文中的顺序编号（0, 1, 2...）。
检索到相关块之后，可以按 chunk_index
排序重组上下文，保持语义连贯。

vector_id — 这个块在 ChromaDB 里的唯一标识符。
格式将会是"{document_id}_{chunk_index}"，比如"3_0"、"3_1"。
通过它可以在 ChromaDB里精确找到或删除对应向量。

---
"""