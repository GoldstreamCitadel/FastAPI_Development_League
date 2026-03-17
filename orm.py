from sqlalchemy.ext.asyncio import create_async_engine
from fastapi import FastAPI
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Float, func
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


app = FastAPI(lifespan=lifespan)

# 6. 添加路由
@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orm:app",reload=True)