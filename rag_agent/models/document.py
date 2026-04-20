import enum

from sqlalchemy import String, Text, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class DocumentStatus(str, enum.Enum):
    # 继承 str 是关键。
    # 普通 enum.Enum 的值是枚举对象，
    # 不能直接序列化成 JSON
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    """
    status用SAEnum — 
    数据库层面约束只能存这四个值，
    插入非法状态会直接报错，
    不会悄悄存进去一个错误数据。
    这是数据完整性保障。
    """
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(DocumentStatus),
        default=DocumentStatus.pending
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )