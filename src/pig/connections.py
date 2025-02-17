import logging
import os
import time
from typing import Optional, Tuple

from .api_client import APIError
from .machines import LocalMachine, RemoteMachine
from .sync_wrapper import _MakeSync

UI_BASE_URL = os.environ.get("PIG_UI_BASE_URL", "https://pig.dev")


class Connection:
    """Represents an active connection to a machine"""

    def __init__(self, machine, connection_id: str) -> None:
        self._client = machine._client
        self.machine = machine
        self.id = connection_id
        self._logger = logging.getLogger(f"pig-{machine.id}")

    @_MakeSync
    async def dimensions(self) -> Tuple[int, int]:
        """Get the dimensions of the machine"""
        route = "computer/display/dimensions"
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        dimensions = await self._client._api_client.get(url, headers=headers)
        return dimensions["width"], dimensions["height"]
    
    @_MakeSync
    async def width(self) -> int:
        """Get the width of the machine"""
        return (await self.dimensions())[0]
    
    @_MakeSync
    async def height(self) -> int:
        """Get the height of the machine"""
        return (await self.dimensions())[1]


    @_MakeSync
    async def key(self, combo: str) -> None:
        """Send a key combo to the machine. Examples: 'a', 'Return', 'alt+Tab', 'ctrl+c ctrl+v'"""

        route = "computer/input/keyboard/key"
        data = {"text": combo}
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)

        await self._client._api_client.post(url, data=data, headers=headers)

    @_MakeSync
    async def type(self, text: str) -> None:
        """Type text into the machine"""
        route = "computer/input/keyboard/type"
        data = {"text": text}
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        await self._client._api_client.post(url, data=data, headers=headers)

    @_MakeSync
    async def cursor_position(self) -> Tuple[int, int]:
        """Get the current cursor position"""
        route = "computer/input/mouse/position"
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        response = await self._client._api_client.get(url, headers=headers)
        return response["x"], response["y"]

    @_MakeSync
    async def mouse_move(self, x: int, y: int) -> None:
        """Move mouse to specified coordinates"""
        route = "computer/input/mouse/move"
        data = {"x": x, "y": y}
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        await self._client._api_client.post(url, data=data, headers=headers)

    async def _mouse_click(self, button: str, down: bool, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Internal method for mouse clicks"""
        route = "computer/input/mouse/click"
        data = {"button": button, "down": down, "x": x, "y": y}
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        await self._client._api_client.post(url, data=data, headers=headers)

    @_MakeSync
    async def left_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Left click at specified coordinates"""
        if x is not None and y is not None:
            await self.mouse_move.aio(x, y)
        await self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)

    @_MakeSync
    async def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Right click at specified coordinates"""
        if x is not None and y is not None:
            await self.mouse_move.aio(x, y)
        await self._mouse_click("right", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("right", False, x, y)

    @_MakeSync
    async def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Double click at specified coordinates"""
        if x is not None and y is not None:
            await self.mouse_move.aio(x, y)
        await self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)
        time.sleep(0.2)
        await self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)

    @_MakeSync
    async def left_click_drag(self, x: int, y: int) -> None:
        """Left click at current cursor position and drag to specified coordinates"""
        await self._mouse_click("left", True)
        time.sleep(0.1)
        await self.mouse_move.aio(x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)

    @_MakeSync
    async def screenshot(self) -> bytes:
        """Take a screenshot of the machine"""
        route = "computer/display/screenshot"
        headers = {"X-Machine-ID": str(self.machine.id), "X-Connection-ID": str(self.id)}
        url = self._client._machine_url(self.machine, route)
        return await self._client._api_client.get(url, expect_json=False, headers=headers)

    @_MakeSync
    async def yield_control(self) -> None:
        """Yield control of the machine to a human operator"""
        if not isinstance(self.machine, RemoteMachine):
            raise APIError(400, "Control operations only available for remote machines")

        url = self._client._api_url(f"machines/{self.machine.id}/pause_bots/true")
        await self._client._api_client.put(url)
        self._logger.info("\nControl has been yielded. \nNavigate to the following URL in your browser to resolve and grant control back to the SDK:")
        self._logger.info(f"-> \033[95m{UI_BASE_URL}/app/machines/{self.machine.id}?connectionId={self.id}\033[0m")

    @_MakeSync
    async def await_control(self) -> None:
        """Awaits for control of the machine to be given back to the bot"""
        if not isinstance(self.machine, RemoteMachine):
            raise APIError(400, "Control operations only available for remote machines")

        min_sleep = 1
        max_sleep = 10
        sleeptime = min_sleep
        while True:
            url = self._client._api_url(f"machines/{self.machine.id}")
            machine = await self._client._api_client.get(url)
            if not machine["pause_bots"]:
                break
            time.sleep(sleeptime)
            sleeptime = min(sleeptime * 2, max_sleep)


class Connections:
    """Namespace for connection operations"""

    def __init__(self, client):
        self._client = client

    @_MakeSync
    async def create(self, machine) -> Connection:
        """Create a new connection to a machine"""
        if isinstance(machine, RemoteMachine):
            url = self._client._api_url(f"machines/{machine.id}/connections")
            response = await self._client._api_client.post(url)
            logger = self._client._logger
            # logger.info("Connected to machine, watch the desktop here:")
            # logger.info(f"-> \033[95m{UI_BASE_URL}/app/machines/{machine.id}?connectionId={response[0]['id']}\033[0m")
            return Connection(machine, response[0]["id"])
        elif isinstance(machine, LocalMachine):
            return Connection(machine, None)

    @_MakeSync
    async def delete(self, machine_id: str, connection_id: Optional[str]) -> None:
        """Delete a connection"""
        if connection_id is not None:
            url = self._client._api_url(f"machines/{machine_id}/connections/{connection_id}")
            await self._client._api_client.delete(url)
