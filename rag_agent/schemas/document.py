from datetime import datetime
from pydantic import BaseModel
from models.document import DocumentStatus
"""
- ORM Model 面向数据库，定义的是"表长什么样"
  - Schema 面向外部接口，定义的是"用户能看到/发来什么"

  这两个边界不应该耦合。比如将来你在表里加一个内部字段
  embedding_vector，你绝对不想把它暴露给 API 调用者——只需要不在    
  Schema 里加这个字段，ORM Model 怎么改都不影响接口。
"""

class DocumentCreate(BaseModel):
    title: str
    content: str


class DocumentRead(BaseModel):
    """
    返回给用户的数据。包含完整信息，
    但注意：将来如果有敏感字段（比如内部处理日志），
    不加进来就不会暴露。
    """
    id: int
    title: str
    content: str
    status: DocumentStatus
    chunk_count: int
    create_time: datetime
    update_time: datetime

    model_config = {"from_attributes": True}
    """
    这是整个文件最重要的一行，只需要写在 DocumentRead 上。

    默认情况下 Pydantic 只能从字典构建对象。但 SQLAlchemy 返回的是   
    ORM 对象，不是字典。加了 from_attributes: True 后，Pydantic      
    会去读对象的属性而不是字典的键，于是 doc.title 能被正确读到。    

    DocumentCreate 不需要这行，因为它只负责接收 JSON
    请求体（本来就是字典），不需要从 ORM 对象转换。
    """

class DocumentList(BaseModel):
    total: int
    items: list[DocumentRead]