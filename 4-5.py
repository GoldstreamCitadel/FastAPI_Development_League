from fastapi import FastAPI
import asyncio
import uvicorn

app = FastAPI()

@app.get("/hi")
async def greet():
    await asyncio.sleep(1)
    return "就一秒?"

if __name__ == "__main__":
    uvicorn.run("4-5:app")