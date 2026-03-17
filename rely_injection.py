from fastapi import FastAPI, Query, Depends

app = FastAPI()

@app.get("/")
async def root():
    return {"message":"Hello World"}

async def common_parameters(
        skip: int = Query(0, ge=0),
        limit: int = Query(10, le=60)
):
    return {"skip":skip, "limit":limit}

@app.get("/news/news_list")
async def root(commons = Depends(common_parameters)):
    return commons

@app.get("/user/user_list")
async def root(commons = Depends(common_parameters)):
    return commons


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("rely_injection:app",reload=True)