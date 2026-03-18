from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from fastapi import FastAPI, Depends
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Float, func, select
from datetime import datetime
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orm:app",reload=True)