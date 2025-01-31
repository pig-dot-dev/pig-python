from typing import TypeVar, Callable, Any, overload, Awaitable, Generic
from typing_extensions import ParamSpec
import asyncio
from pig import _MakeSync, AsyncContextError

class MyClass():
    @_MakeSync
    async def hi(self) -> None:
        await asyncio.sleep(0.1)
        print("hi")
    
    @_MakeSync
    async def greet(self, name: str) -> str:
        return f"Hello {name}!"

# test section
obj = MyClass()

# sync (outside async loop)
obj.hi()
print(obj.greet("World"))

# within async loop
async def do_async():
    # async
    await obj.hi.aio() 
    print(await obj.greet.aio("World"))

    # sync (within async loop)
    try:
        obj.hi()
    except AsyncContextError as e:
        print("Caught expected exception")
        print(e)

asyncio.run(do_async())