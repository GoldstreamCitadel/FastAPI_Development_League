import asyncio

async def q():
    print("您猜那大哥说什么来着？")
    await asyncio.sleep(3)

async def a():
    print("看什么看！没见过擦玻璃的吗！")

async def main():
    await asyncio.gather(q(), a())
    print("到这才结束呢。")

asyncio.run(main())