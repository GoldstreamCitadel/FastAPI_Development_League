from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db

router = APIRouter()
"""
---
  设计目的

  Health Check
  是工业项目的标配接口。它回答一个问题："服务现在能正常工作吗？"   
  Kubernetes、负载均衡器、监控系统（Prometheus、Uptime
  Robot）都会定期 GET 这个接口——返回 200 就继续发流量，返回 500    
  就把这个实例摘掉。

  ---
   真实项目的 health check 往往分两层：
  - /health/live：进程活没活（不查 DB，只返回 200）
  - /health/ready：服务准备好没有（查 DB、查外部依赖）

  Kubernetes 的 livenessProbe 和 readinessProbe
  分别打这两个接口。我们现在写的是简化版，后面阶段7生产化时会拆开。
"""

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
