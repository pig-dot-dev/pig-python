import logging
import os
import time
from typing import Any, Dict, Optional, Tuple, Union

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client import ClientResponse, ClientResponseError
from aiohttp_retry import ExponentialRetry, RetryClient

from .sync_wrapper import _MakeSync

try:
    from importlib.metadata import version

    __version__ = version("pig-python")
except Exception:
    __version__ = "unknown"

BASE_URL = "https://api.pig.dev"
if os.environ.get("PIG_BASE_URL"):
    BASE_URL = os.environ["PIG_BASE_URL"]
    if BASE_URL.endswith("/"):
        BASE_URL = BASE_URL[:-1]

UI_BASE_URL = "https://pig.dev"
if os.environ.get("PIG_UI_BASE_URL"):
    UI_BASE_URL = os.environ["PIG_UI_BASE_URL"]
    if UI_BASE_URL.endswith("/"):
        UI_BASE_URL = UI_BASE_URL[:-1]


class APIError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class VMError(Exception):
    """Base exception for VM-related errors"""

    pass


class APIClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _session(self) -> RetryClient:
        retry_options = ExponentialRetry(
            attempts=float("inf"),  # Infinite retries
            start_timeout=0.1,
            max_timeout=60,  # Max delay of 60 seconds between retries
            factor=1.3,  # Exponential backoff factor
            statuses={503},  # Only retry on 503 status
        )

        session = ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Client-Language": "python",
                "X-Client-Version": __version__,
            },
            timeout=ClientTimeout(total=90),  # 15 minute total timeout
        )

        retry_client = RetryClient(client_session=session, retry_options=retry_options)

        return retry_client

    async def _handle_response(self, response: ClientResponse, expect_json: bool = True) -> Union[Dict[str, Any], bytes]:
        try:
            response.raise_for_status()

            # If no content, return empty dict
            if not response.content or response.content_length == 0:
                return {}

            # if we're expecting json
            if expect_json:
                if not response.content_type.startswith("application/json"):
                    raise APIError(response.status, f"Expected JSON response but got content-type: {response.content_type}")
                return await response.json() if response.content else {}

            # else it's a stream reader. Drain it
            body = await response.read()
            return body

        except ClientResponseError as e:
            error_msg = str(e)
            if response.content:
                try:
                    if response.content_type.startswith("application/json"):
                        error_msg = (await response.json()).get("detail", str(e))
                except:  # noqa: E722
                    pass
            raise APIError(response.status, error_msg) from e

    async def get(self, endpoint: str, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        endpoint = endpoint.lstrip("/")
        async with self._session() as session:
            async with session.get(f"{self.base_url}/{endpoint}") as response:
                return await self._handle_response(response, expect_json)

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        endpoint = endpoint.lstrip("/")
        async with self._session() as session:
            async with session.post(f"{self.base_url}/{endpoint}", json=data) as response:
                return await self._handle_response(response, expect_json)

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        endpoint = endpoint.lstrip("/")
        async with self._session() as session:
            async with session.put(f"{self.base_url}/{endpoint}", json=data) as response:
                return await self._handle_response(response)

    async def delete(self, endpoint: str) -> None:
        endpoint = endpoint.lstrip("/")
        async with self._session() as session:
            async with session.delete(f"{self.base_url}/{endpoint}") as response:
                await self._handle_response(response)


class Connection:
    """Represents an active connection to a VM"""

    def __init__(self, vm: "VM", connection_id: str) -> None:
        self.api = vm.api
        self.vm_id = vm.id
        self.id = connection_id
        self._logger = vm._logger

    @property
    def width(self) -> int:
        """Get the width of the VM"""
        return 1024

    @property
    def height(self) -> int:
        """Get the height of the VM"""
        return 768

    @_MakeSync
    async def yield_control(self) -> None:
        """Yield control of the VM to a human operator"""
        await self.api.put(f"vms/{self.vm_id}/pause_bots/true")
        self._logger.info("\nControl has been yielded. \nNavigate to the following URL in your browser to resolve and grant control back to the SDK:")
        self._logger.info(f"-> \033[95m{UI_BASE_URL}/app/vms/{self.vm_id}?connectionId={self.id}\033[0m")

    @_MakeSync
    async def await_control(self) -> None:
        """Awaits for control of the VM to be given back to the bot"""
        min_sleep = 1
        max_sleep = 10
        sleeptime = min_sleep
        while True:
            vm = await self.api.get(f"vms/{self.vm_id}")
            if not vm["pause_bots"]:
                break
            time.sleep(sleeptime)
            sleeptime += 1
            if sleeptime > max_sleep:
                sleeptime = max_sleep

    @_MakeSync
    async def key(self, combo: str) -> None:
        """Send a XDO key combo to the VM. Examples: 'a', 'Return', 'alt+Tab', 'ctrl+c ctrl+v'"""
        await self.api.post(
            f"vms/{self.vm_id}/key?connection_id={self.id}",
            data={
                "string": combo,
            },
        )

    @_MakeSync
    async def type(self, text: str) -> None:
        """Type text into the VM"""
        await self.api.post(
            f"vms/{self.vm_id}/type?connection_id={self.id}",
            data={
                "string": text,
            },
        )

    @_MakeSync
    async def cursor_position(self) -> Tuple[int, int]:
        """Get the current cursor position"""
        response = await self.api.get(f"vms/{self.vm_id}/cursor_position?connection_id={self.id}")
        return response["x"], response["y"]

    @_MakeSync
    async def mouse_move(self, x: int, y: int) -> None:
        """Move mouse to specified coordinates"""
        await self.api.post(
            f"vms/{self.vm_id}/mouse_move?connection_id={self.id}",
            data={
                "x": x,
                "y": y,
            },
        )

    @_MakeSync
    async def left_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Left click at specified coordinates"""
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
    async def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Double click at specified coordinates"""
        await self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)
        time.sleep(0.2)
        await self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("left", False, x, y)

    @_MakeSync
    async def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Right click at specified coordinates"""
        await self._mouse_click("right", True, x, y)
        time.sleep(0.1)
        await self._mouse_click("right", False, x, y)

    async def _mouse_click(self, button: str, down: bool, x: Optional[int] = None, y: Optional[int] = None) -> None:
        await self.api.post(
            f"vms/{self.vm_id}/mouse_click?connection_id={self.id}",
            data={
                "button": button,
                "down": down,
                "x": x,
                "y": y,
            },
        )

    @_MakeSync
    async def screenshot(self) -> bytes:
        """Take a screenshot of the VM"""
        response = await self.api.get(f"vms/{self.vm_id}/screenshot?connection_id={self.id}", expect_json=False)
        return response

    @_MakeSync
    async def powershell(self, command: str, close_after: bool = False) -> None:
        """Execute a PowerShell command in the VM"""
        await self.api.post(
            f"vms/{self.vm_id}/powershell?connection_id={self.id}",
            data={
                "command": command,
                "close_after": close_after,
            },
        )

    @_MakeSync
    async def cmd(self, command: str, close_after: bool = False) -> None:
        """Execute a CMD command in the VM"""
        await self.api.post(
            f"vms/{self.vm_id}/cmd?connection_id={self.id}",
            data={
                "command": command,
                "close_after": close_after,
            },
        )


class VMSession:
    """Context manager for VM sessions"""

    def __init__(self, vm: "VM") -> None:
        self.vm = vm
        self.connection = None

    def __enter__(self) -> Connection:
        self.connection = self.vm.connect()
        return self.connection

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.connection:
            if self.vm._temporary:
                self.vm.terminate()
            else:
                self.vm.stop()

    async def __aenter__(self) -> Connection:
        self.connection = await self.vm.connect.aio()
        return self.connection

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.connection:
            if self.vm._temporary:
                await self.vm.terminate.aio()
            else:
                await self.vm.stop.aio()


class Windows:
    """Windows image configuration"""

    def __init__(self, version: str = "2025") -> None:
        self.version = version
        self.installs = []

    def install(self, application: str) -> "Windows":
        """Add an application to be installed"""
        self.installs.append(application)
        return self

    def _to_dict(self) -> dict:
        return {"version": self.version, "installs": self.installs}


class VM:
    """Main class for VM management"""

    def __init__(
        self,
        id: Optional[str] = None,
        image: Optional[Union[Windows, str]] = None,
        temporary: bool = False,
        api_key: Optional[str] = None,
        log_level: str = "INFO",
    ) -> None:
        self.api_key = api_key or os.environ.get("PIG_SECRET_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either as argument or PIG_SECRET_KEY environment variable")

        self.api = APIClient(BASE_URL, self.api_key)
        self._id = id
        self._temporary = temporary
        self._image = image  # could be a Windows object or string id

        self._logger = logging.getLogger(f"pig-{id}")
        self._logger.setLevel(log_level)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.handlers = [handler]

        if id and temporary:
            raise ValueError("Cannot use an existing VM as a temporary VM, since temporary VMs are destroyed after use.")

    @_MakeSync
    async def session(self) -> VMSession:
        """Create a new session for this VM.

        Can be used as either a sync or async context manager:

        Sync usage:
            with vm.session() as conn:
                # use connection
                conn.type("Hello, World!")

        Async usage:
            async with vm.session.aio() as conn:
                # use connection
                await conn.type("Hello, World!")
        """
        return VMSession(self)

    @_MakeSync
    async def create(self) -> str:
        """Create a new VM"""
        if self._id:
            raise VMError("VM already exists")

        if isinstance(self._image, str):
            # User provided an id
            data = {"image_id": self._image}
        else:
            # handle Windows image format
            # to deprecate
            data = self._image._to_dict() if self._image else None

        response = await self.api.post("vms", data=data)
        self._id = response[0]["id"]
        return self._id

    @_MakeSync
    async def connect(self) -> Connection:
        """Connect to the VM, creating it if necessary"""
        if not self._id:
            await self.create.aio()
        vm = await self.api.get(f"vms/{self._id}")
        if vm["status"] == "Terminated":
            raise VMError(f"VM {self._id} is terminated")

        if vm["status"] != "Running":
            await self.start.aio()

        response = await self.api.post(f"vms/{self._id}/connections")
        self._logger.info("Connected to VM, watch the desktop here:")
        self._logger.info(f"-> \033[95m{UI_BASE_URL}/app/vms/{self._id}?connectionId={response[0]['id']}\033[0m")

        return Connection(self, response[0]["id"])

    @_MakeSync
    async def start(self) -> None:
        """Start the VM"""
        if not self._id:
            raise VMError("VM not created")
        await self.api.put(f"vms/{self._id}/state/start")

    @_MakeSync
    async def stop(self) -> None:
        """Stop the VM"""
        if not self._id:
            raise VMError("VM not created")
        await self.api.put(f"vms/{self._id}/state/stop")

    @_MakeSync
    async def terminate(self) -> None:
        """Terminate and delete the VM"""
        if not self._id:
            raise VMError("VM not created")
        await self.api.delete(f"vms/{self._id}")

    @property
    def id(self) -> Optional[str]:
        """Get the VM ID"""
        return self._id
