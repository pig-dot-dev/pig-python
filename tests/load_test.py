import asyncio
import os
import aiohttp
import random
from pig import Client, RemoteMachine

client = Client()

# this level of concurrency only supported by teams with this much quota
# (default max is 3)
n = 10

base_url = os.environ["PIG_BASE_URL"]

async def fetch_stream(vm_id: str):
    i = 0
    endpoint = f"{base_url}/vms/{vm_id}/video-stream"
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoint) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch stream: {response.status}")
            async for chunk in response.content.iter_chunked(1024):
                i += 1
                if i > 1000:
                    break
                pass

async def test_load():
    await asyncio.sleep(random.randint(0, 10))
    async with client.machines.temporary.aio() as vm:
        async with vm.connect.aio() as conn:
            stream_coro = fetch_stream(vm.id) 
            for x in range(0, 100, 10):
                for y in range(0, 100, 10):
                    await conn.mouse_move.aio(x=x, y=y)
                    await conn.type.aio("hello")

        await stream_coro

if __name__ == "__main__":
    async def spawn_many():
        coros = [test_load() for _ in range(n)]
        await asyncio.gather(*coros)
   
    asyncio.run(spawn_many())