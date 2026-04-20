from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.document import Document
from schemas.document import DocumentCreate
"""
Service 层是业务逻辑的家。它不知道 HTTP 存在，
不碰Request、Response，只做一件事：
接收数据，操作数据库，返回结果。  

这意味着将来你要写单元测试，
只需要给 Service 注入一个测试用的 db session，
完全不需要启动 HTTP 服务器。
Router层和业务逻辑解耦之后，两边都好测。
"""

class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: DocumentCreate) -> Document:
        doc = Document(**data.model_dump()) #解包
        self.db.add(doc)

        """
        flush 把变更发送给数据库执行SQL,但不提交事务。
        这意味着数据库已经分配了 id,
        你可以用 refresh 把自动生成的 id、create_time 
        等字段同步回 Python 对象。

        commit 才是真正提交。而 commit 在哪里？
        在 database.py 的 get_db()里——
        请求成功返回时自动提交，出异常时自动回滚。
        Service层不需要也不应该自己 commit,否则事务边界就乱了。
        """

        await self.db.flush()
        await self.db.refresh(doc)
        return doc
    
    async def get(self, doc_id: int) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, skip: int=0, limit: int=20) -> tuple[int, list[Document]]:
        """
        两条查询：先查总数，再查当前页数据。
        total给前端做分页导航用，
        offset/limit控制返回哪一页。
        scalars() 把 Row 对象列表转成 ORM 对象列表，
        list() 强制求值（否则是懒加载迭代器，
        session 关闭后会出错）。
        """
        total = await self.db.scalar(
            select(func.count()).select_from(Document)
        )
        result = await self.db.execute(
            select(Document).offset(skip).limit(limit)
        )
        return total, list(result.scalars().all())
    
    async def delete(self, doc: Document) -> None:
        await self.db.delete(doc)
        await self.db.flush()