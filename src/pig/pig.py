import logging
import os
from typing import Optional
from urllib.parse import urljoin

from .api_client import APIClient
from .machines import Machines, MachineType
from .connections import Connections

def base_url(machine_type: MachineType) -> str:
    """Get the base URL for a given machine type"""
    if machine_type == MachineType.LOCAL:
        base = os.environ.get("PIG_LOCAL_URL", "http://localhost:3000")
    else:
        base = os.environ.get("PIG_BASE_URL", "https://api.pig.dev")
    
    return base.rstrip("/")

class Client:
    """Main client for interacting with the Pig API"""

    def __init__(self, api_key: Optional[str] = None, log_level: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("PIG_SECRET_KEY") # can be None for LocalMachine
        self._logger = self._setup_logger(log_level)
        self._api_client = APIClient(self.api_key)
        self._remote_base = base_url(MachineType.REMOTE)
        self._local_base = base_url(MachineType.LOCAL)
        self.machines = Machines(self)
        self.connections = Connections(self)

    def _url(self, machine_type: MachineType, path: str) -> str:
        """Construct full URL for a given machine type and path"""
        base = self._local_base if machine_type == MachineType.LOCAL else self._remote_base
        return urljoin(f"{base}/", path)

    def _setup_logger(self, log_level: Optional[str] = None) -> logging.Logger:
        """Setup logging for the client"""
        logger = logging.getLogger("pig")
        if log_level:
            logger.setLevel(getattr(logging, log_level.upper()))
        else:
            logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.handlers = [handler]
        return logger
