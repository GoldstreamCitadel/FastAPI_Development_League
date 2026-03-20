from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Float, func, select
from datetime import datetime
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from pydantic import BaseModel

load_dotenv() #.env



# 1.create async engine
password = os.getenv("MYSQL_DB_PASSWORD")
ASYNC_DATABASE_URL = "mysql+aiomysql://root:"+password+"@localhost:3306/FastAPI_first?charset=utf8"
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True, # sql log
    pool_size=10,
    max_overflow=20
)

# 2.define model class
class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(),default=func.now, comment="创建时间")
    update_time: Mapped[datetime] = mapped_column(DateTime, insert_default=func.now(),default=func.now, onupdate=func.now(), comment="创建时间")

class Book(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True, comment="书籍id")
    bookname: Mapped[str] = mapped_column(String(255), comment="书名")
    author: Mapped[str] = mapped_column(String(255), comment="作者")
    price: Mapped[float] = mapped_column(Float, comment="价格")
    publisher: Mapped[str] = mapped_column(String(255), comment="出版社")



# 3.建表，fastapi 启动时
async def create_tables():
    # get engine, create events, make tabulates
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) # Base model class row data
    print(">>> DB Table creation done.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(">>> FastAPI app launching...")
    await create_tables()

    yield

    print(">>> FastAPI app closing...")
    await async_engine.dispose()
    print(">>> Database connection shut down.")


# 查询 依赖注入 会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind = async_engine, #绑定数据库引擎
    class_ = AsyncSession, #指定会话类
    expire_on_commit = False, #提交后会话不过期，不重新查库，高性能
)

# 依赖项
async def get_database():
    async with AsyncSessionLocal() as session:
        try:
            yield session #返回数据库会话给router func
            await session.commit() #提交事务
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close() #一定要关

app = FastAPI(lifespan=lifespan)

# 6. 添加路由
# 函数重名不影响，关键是路由匹配不要冲突
@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/books/all")
async def get_book_list(db: AsyncSession = Depends(get_database)):
    # 查询
    result = await db.execute(select(Book)) #orm结果
    book = result.scalars().all()
    return book

@app.get("/books/one")
async def get_book_list(db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book)) #orm结果
    book = result.scalars().first()
    return book

@app.get("/books/key")
async def get_book_list(db: AsyncSession = Depends(get_database)):
    book = await db.get(Book, 2) #直接get，按类和主键查
    return book

@app.get("/books/price")
async def get_book_list_price(db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book).where(Book.price >= 100))
    book = result.scalars().all()
    return book

@app.get("/books/find_yu")
async def get_book_list_price(db: AsyncSession = Depends(get_database)):
    # result = await db.execute(select(Book).where(Book.author.like("%于%")))
    result = await db.execute(select(Book).where(Book.author.like("%于%") | Book.bookname.like("%于%")))
    book = result.scalars().all()
    return book

@app.get("/books/find_guo_100+")
async def get_book_list_price(db: AsyncSession = Depends(get_database)):
    # bool逻辑运算，注意优先级，不加括号易错
    result = await db.execute(select(Book).where(Book.author.like("郭_纲%") & (Book.price >= 100)))
    book = result.scalars().all()
    return book

@app.get("/books/find_east_west_single")
async def get_book_list_price(db: AsyncSession = Depends(get_database)):
    bookmarkets = ["东单书城","西单书城"]
    result = await db.execute(select(Book).where(Book.publisher.in_(bookmarkets)))
    book = result.scalars().all()
    return book

# 路由从定向下依次找匹配，如果把有传参的放前面，可能会和后面的冲突
@app.get("/books/last_avoid_conflict/{id}")
async def get_book_list(id:int, db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(Book).where(Book.id == id))
    book = result.scalar_one_or_none()
    return book

# 下面是聚合查询
@app.get("/book/avg_p")
async def get_avg_price(db: AsyncSession = Depends(get_database)):
    # select里面跟两个好像只能返回第一个，不报错倒是
    result = await db.execute(select(func.max(Book.price), func.sum(Book.price), func.avg(Book.price)))
    count = result.scalars().all()
    return count

@app.get("/book/get_count")
async def get_avg_price(db: AsyncSession = Depends(get_database)):
    result = await db.execute(select(func.count(Book.id)))
    count = result.scalar() # 提取一个标量值
    return count

# 分页查询
@app.get("/book/get_book_list")
async def get_book_list(
    page: int = 1,
    page_size: int = 3,
    db: AsyncSession = Depends(get_database)
):
    result = await db.execute(select(Book).offset((page-1)*page_size).limit(page_size))
    books = result.scalars().all()
    return books

# 用户请求体类型
class BookBase(BaseModel):
    id: int
    bookname: str
    author: str
    price: float
    publisher: str

"""
今天涨了一记性，您以为是请求体格式问题，结果是路由错了
"""

# 增 输入信息，新增入库
@app.post("/book/add_book")
async def add_book(book: BookBase, db: AsyncSession = Depends(get_database)):
    # ORM obj -> add -> commit
    book_obj = Book(**book.__dict__)
    db.add(book_obj)
    await db.commit()
    return book

from pydantic import BaseModel
# 之前导过 再导一次 看下是不是真的闹鬼了

class BookUpdate(BaseModel):
    bookname: str
    author: str
    price: float
    publisher: str
    class Config:
        schema_extra = {
            "example": {
                "bookname": "新书名",
                "author": "新作者",
                "price": 29.99,
                "publisher": "新出版社"
            }
        }


# 改 先查找，再修改 得有请求体，传新参
@app.put("/book/update_book/{book_id}")
async def update_book(book_id: int, data: BookUpdate, db: AsyncSession = Depends(get_database)):
    db_book = await db.get(Book, book_id)
    if db_book is None:
        raise HTTPException(
            status_code = 404,
            detail = "您要找的家伙，咱这地儿确实没有。您上谦儿哥那床底下找去。"
        )
    # 找到 重新赋值
    db_book.bookname = data.bookname
    db_book.author = data.author
    db_book.price = data.price
    db_book.publisher = data.publisher

    await db.commit() ###这里边儿不能包馅儿，请求体已经传参了
    return db_book


# 删 先查找，再删除
@app.delete("/book/delete_book/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_database)):
    db_book = await db.get(Book, book_id)
    if db_book is None:
        raise HTTPException(
            status_code = 404,
            detail = "真没找到"
        )

    await db.delete(db_book)
    await db.commit()
    return {"msg":"得嘞，我这就给您扔喽"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orm:app",reload=True)