import os
import time
from typing import Any, Dict, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = self._create_session()
        self._team_id = None

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        return session

    def _handle_response(self, response: requests.Response, expect_json: bool = True) -> Union[Dict[str, Any], requests.Response]:
        try:
            response.raise_for_status()
            if expect_json:
                return response.json() if response.content else {}
            return response
        except requests.exceptions.HTTPError as e:
            error_msg = str(e)
            if response.content:
                try:
                    error_msg = response.json().get('detail', str(e))
                except:  # noqa: E722
                    pass
            raise APIError(response.status_code, error_msg) from e

    def get(self, endpoint: str, expect_json: bool = True) -> Union[Dict[str, Any], requests.Response]:
        response = self.session.get(f"{self.base_url}/{endpoint}")
        return self._handle_response(response, expect_json)

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], requests.Response]:
        response = self.session.post(f"{self.base_url}/{endpoint}", json=data)
        return self._handle_response(response, expect_json)

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.session.put(f"{self.base_url}/{endpoint}", json=data)
        return self._handle_response(response)

    def delete(self, endpoint: str) -> None:
        response = self.session.delete(f"{self.base_url}/{endpoint}")
        self._handle_response(response)

    @property
    def team_id(self) -> str:
        if self._team_id is None:
            self._team_id = self.get("teams/me")
        return self._team_id

class Connection:
    """Represents an active connection to a VM"""
    def __init__(self, id: str, api_client: APIClient, vm_id: str) -> None:
        self.api = api_client
        self.vm_id = vm_id
        self.id = id

    @property
    def width(self) -> int:
        """Get the width of the VM"""
        return 1024

    @property
    def height(self) -> int:
        """Get the height of the VM"""
        return 768

    def yield_control(self) -> None:
        """Yield control of the VM to a human operator"""
        self.api.put(f"vms/{self.vm_id}/rdp-connections/{self.id}/block_bot/true")
        print("\nControl has been yielded. \nNavigate to the following URL in your browser to resolve and grant control back to the SDK:")
        print(f"-> \033[95m{UI_BASE_URL}/vms/{self.vm_id}/rdp-connections/{self.id}\033[0m")


    def await_control(self) -> None:
        """Awaits for control of the VM to be given back to the bot"""
        min_sleep = 1
        max_sleep = 10 # seconds
        sleeptime = min_sleep
        while True:
            conn = self.api.get(f"vms/{self.vm_id}/rdp-connections/{self.id}")
            if not conn["block_bot"]:
                break
            time.sleep(sleeptime)
            sleeptime += 1
            if sleeptime > max_sleep:
                sleeptime = max_sleep

    def key(self, combo: str) -> None:
        """Send a XDO key combo to the VM. Examples: 'a', 'Return', 'alt+Tab', 'ctrl+c ctrl+v'"""
        self.api.post(f"vms/{self.vm_id}/rdp-connections/{self.id}/key", data={
            "string": combo,
        })

    def type(self, text: str) -> None:
        """Type text into the VM"""
        self.api.post(f"vms/{self.vm_id}/rdp-connections/{self.id}/type", data={
            "string": text,
        })

    def cursor_position(self) -> Tuple[int, int]:
        """Get the current cursor position"""
        response = self.api.get(f"vms/{self.vm_id}/rdp-connections/{self.id}/cursor_position")
        return response["x"], response["y"]
        
    def mouse_move(self, x: int, y: int) -> None:
        """Move mouse to specified coordinates"""
        self.api.post(f"vms/{self.vm_id}/rdp-connections/{self.id}/mouse_move", data={
            "x": x,
            "y": y,
        })

    def left_click(self, x: int | None = None, y: int | None = None) -> None:
        """Left click at specified coordinates"""
        self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        self._mouse_click("left", False, x, y)

    def left_click_drag(self, x: int, y: int) -> None:
        """Left click at current cursor position and drag to specified coordinates"""
        # Press
        self._mouse_click("left", True)
        time.sleep(0.1)
        # drag to destination
        self.mouse_move(x, y)
        time.sleep(0.1)
        # Release
        self._mouse_click("left", False, x, y)

    def double_click(self, x: int | None = None, y: int | None = None) -> None:
        """Double click at specified coordinates"""
        self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        self._mouse_click("left", False, x, y)
        time.sleep(0.2)
        self._mouse_click("left", True, x, y)
        time.sleep(0.1)
        self._mouse_click("left", False, x, y)

    def right_click(self, x: int | None = None, y: int | None = None) -> None:
        """Right click at specified coordinates"""
        self._mouse_click("right", True, x, y)
        time.sleep(0.1)
        self._mouse_click("right", False, x, y)

    # def middle_click(self, x: int, y: int) -> None:
    #     """Middle click at specified coordinates"""
    #     raise NotImplementedError("middle_click() is not implemented yet")

    def _mouse_click(self, button: str, down: bool, x: int | None = None, y: int | None = None) -> None:
        self.api.post(f"vms/{self.vm_id}/rdp-connections/{self.id}/mouse_click", data={
            "button": button,
            "down": down,
            "x": x,
            "y": y,
        })

    def screenshot(self) -> bytes:
        """Take a screenshot of the VM"""
        response = self.api.get(f"vms/{self.vm_id}/rdp-connections/{self.id}/screenshot", expect_json=False)
        return response.content

class VMSession:
    """Context manager for VM sessions"""
    def __init__(self, vm: 'VM') -> None:
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

class Windows:
    """Windows image configuration"""
    def __init__(self, version: str = "2025") -> None:
        self.version = version
        self.installs = []

    def install(self, application: str) -> 'Windows':
        """Add an application to be installed"""
        self.installs.append(application)
        return self

    def _to_dict(self) -> dict:
        return {
            "version": self.version,
            "installs": self.installs
        }

class VM:
    """Main class for VM management"""
    def __init__(self, id: Optional[str] = None, image: Optional[Windows] = None, temporary: bool = False, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("PIG_SECRET_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either as argument or PIG_SECRET_KEY environment variable")

        self.api = APIClient(BASE_URL, self.api_key)
        self._id = id
        self._temporary = temporary
        self._image = image

        if id and temporary:
            raise ValueError("Cannot use an existing VM as a temporary VM, since temporary VMs are destroyed after use.")

    def session(self) -> VMSession:
        """Create a new session for this VM"""
        return VMSession(self)

    def create(self) -> str:
        """Create a new VM"""
        if self._id:
            raise VMError("VM already exists")

        data = self._image._to_dict() if self._image else None
        response = self.api.post(f"teams/{self.api.team_id}/vms", data=data)
        self._id = response[0]["id"]
        return self._id

    def connect(self) -> Connection:
        """Connect to the VM, creating it if necessary"""
        if not self._id:
            self.create() # creates a new VM if not exists

        # Get VM status
        vm = self.api.get(f"teams/{self.api.team_id}/vms/{self._id}")
        if vm["status"] == "Terminated":
            raise VMError(f"VM {self._id} is terminated")

        # Start VM if needed
        if vm["status"] == "Stopped":
            self.start()

        # Create RDP connection
        response = self.api.post(f"vms/{self._id}/rdp-connections")
        print("Connected to VM, watch the desktop here:")
        print(f"-> \033[95m{UI_BASE_URL}/vms/{self._id}/rdp-connections/{response[0]['id']}\033[0m")
        return Connection(response[0]["id"], self.api, self._id )

    def start(self) -> None:
        """Start the VM"""
        if not self._id:
            raise VMError("VM not created")
        self.api.put(f"teams/{self.api.team_id}/vms/{self._id}/state/start")

    def stop(self) -> None:
        """Stop the VM"""
        if not self._id:
            raise VMError("VM not created")
        self.api.put(f"teams/{self.api.team_id}/vms/{self._id}/state/stop")

    def terminate(self) -> None:
        """Terminate and delete the VM"""
        if not self._id:
            raise VMError("VM not created")
        self.api.delete(f"teams/{self.api.team_id}/vms/{self._id}")

    @property
    def id(self) -> Optional[str]:
        """Get the VM ID"""
        return self._id