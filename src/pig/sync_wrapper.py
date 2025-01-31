import asyncio
from typing import Any, Awaitable, Callable, Generic, TypeVar, overload

from typing_extensions import ParamSpec

T = TypeVar("T")  # Return type
P = ParamSpec("P")  # Parameters


class AsyncContextError(Exception):
    """Raised when a sync method is called in an async context"""

    pass


class _MakeSync(Generic[P, T]):
    @overload
    def __get__(self, obj: None, objtype: Any) -> "_MakeSync[P, T]": ...

    @overload
    def __get__(self, obj: Any, objtype: Any) -> Callable[P, T]: ...

    def __init__(self, func: Callable[P, Awaitable[T]]) -> None:
        self.async_func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                asyncio.get_running_loop()
                raise AsyncContextError(
                    f"Pig method {obj.__class__.__name__}.{self.async_func.__name__}() "
                    f"cannot be called in an async context. Use {obj.__class__.__name__}."
                    f"{self.async_func.__name__}.aio() instead"
                )
            except RuntimeError:
                # Happy path - no running loop - safe to use asyncio.run
                return asyncio.run(aio_wrapper(*args, **kwargs))

        async def aio_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result = await self.async_func(obj, *args, **kwargs)
            return result

        class AsyncContextWrapper:
            """Wrapper that provides an async context manager interface"""

            def __init__(self, coro: Awaitable[T]):
                self.coro = coro
                self._obj = None

            def __await__(self):
                async def _await():
                    if not self._obj:
                        self._obj = await self.coro
                    return self._obj

                return _await().__await__()

            async def __aenter__(self):
                if not self._obj:
                    self._obj = await self.coro
                if hasattr(self._obj, "__aenter__"):
                    return await self._obj.__aenter__()
                return self._obj

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if hasattr(self._obj, "__aexit__"):
                    await self._obj.__aexit__(exc_type, exc_val, exc_tb)

        def aio(*args: P.args, **kwargs: P.kwargs) -> AsyncContextWrapper:
            return AsyncContextWrapper(aio_wrapper(*args, **kwargs))

        sync_wrapper.aio = aio
        return sync_wrapper
