from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from database import create_tables

from models import document as _doc_model #  noqa: F401
from models import chunk as _chunk_model # noqa: F401

from api.v1.routers import health

"""
只干三件事：创建 app实例、
注册启动/关闭钩子、挂载所有路由。
它本身不写任何业务逻辑——
这是工业项目的铁律，main.py 越薄越好。
"""

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(health.router,
                   prefix="/api/v1",tags=["health"])

from api.v1.routers import document
app.include_router(
    document.router,
    prefix="/api/v1",
    tags=["documents"]
)
