import logging
import os
from typing import Optional
from urllib.parse import urljoin

from .api_client import APIClient
from .connections import Connections
from .machines import Machines, MachineType, RemoteMachine


class Client:
    """Main client for interacting with the Pig API"""

    def __init__(self, api_key: Optional[str] = None, log_level: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("PIG_SECRET_KEY")  # can be None for LocalMachine
        self._logger = self._setup_logger(log_level)
        self._api_client = APIClient(self.api_key)

        self._api_base = os.environ.get("PIG_API_URL", "https://api2.pig.dev").rstrip("/")  # API for remote machines
        self._proxy_base = os.environ.get("PIG_PROXY_URL", "https://proxy.pig.dev").rstrip("/")  # Proxy API for remote machines
        self._local_base = os.environ.get("PIGLET_LOCAL_URL", "http://localhost:3000").rstrip("/")  # Local server for local piglet

        self.machines = Machines(self)
        self.connections = Connections(self)

    def _machine_url(self, machine: MachineType, path: str) -> str:
        if isinstance(machine, RemoteMachine):
            return urljoin(f"{self._proxy_base}/", path)
        else:
            return urljoin(f"{self._local_base}/", path)

    def _api_url(self, path: str) -> str:
        """Construct full URL for a given path"""
        return urljoin(f"{self._api_base}/", path)

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
