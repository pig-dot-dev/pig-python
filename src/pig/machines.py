import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from .api_client import APIError
from .connection_session import ConnectionSession
from .sync_wrapper import _MakeSync

class MachineType(Enum):
    LOCAL = "local"
    REMOTE = "remote"

class Machine(ABC):
    """Abstract base class for all machine types"""
    @abstractmethod
    def connect(self):
        pass

class RemoteMachine(Machine):
    """A remote machine on Pig"""
    def __init__(self, client, id: str = None):
        self._client = client
        self.id = id
        self._ephemeral = False

    # Sync context manager
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self._ephemeral:
            self._client.machines.delete(self.id)

    # Async context manager
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self._ephemeral:
            await self._client.machines.delete.aio(self.id)

    def _set_ephemeral(self, ephemeral: bool):
        self._ephemeral = ephemeral

    @_MakeSync
    async def connect(self):
        """Get a connection to this machine. Use as an async context manager:
        
        async with machine.connect() as conn:
            await conn.mouse_move(x=100, y=100)

        or as a sync context manager:
        
        with machine.connect() as conn:
            conn.mouse_move(x=100, y=100)
        """
        return ConnectionSession(self)

    @_MakeSync
    async def start(self) -> None:
        """Start the machine"""
        if not self.id:
            raise APIError(400, "Machine not created")
        url = self._client._url(MachineType.REMOTE, f"vms/{self.id}/state/start")
        await self._client._api_client.put(url)

    @_MakeSync
    async def stop(self) -> None:
        """Stop the machine"""
        if not self.id:
            raise APIError(400, "Machine not created")
        url = self._client._url(MachineType.REMOTE, f"vms/{self.id}/state/stop")
        await self._client._api_client.put(url)

    @_MakeSync
    async def terminate(self) -> None:
        """Terminate and delete the machine"""
        if not self.id:
            raise APIError(400, "Machine not created")
        url = self._client._url(MachineType.REMOTE, f"vms/{self.id}")
        await self._client._api_client.delete(url)

class LocalMachine(Machine):
    """A local machine running on localhost"""
    def __init__(self, client):
        self._client = client
        self.id = "local"

    def connect(self):
        return ConnectionSession(self)

class Machines:
    """This class communicates with the API for CRUD operations on machines"""
    def __init__(self, client):
        self._client = client

    @_MakeSync
    async def create(self, image_id: Optional[str] = None) -> RemoteMachine:
        """Create a new remote machine"""
        url = self._client._url(MachineType.REMOTE, "vms")
        data = {"image_id": image_id} if image_id else None
        response = await self._client._api_client.post(url, data=data)
        machine_id = response[0]["id"]
        return RemoteMachine(self._client, machine_id)

    @_MakeSync
    async def delete(self, id: str) -> None:
        """Delete a remote machine"""
        url = self._client._url(MachineType.REMOTE, f"vms/{id}")
        await self._client._api_client.delete(url)

    @_MakeSync
    async def temporary(self) -> RemoteMachine:
        """Create a temporary remote machine that will be deleted after use"""
        machine = await self.create.aio()
        machine._set_ephemeral(True)
        return machine

    @_MakeSync
    async def get(self, id: str) -> RemoteMachine:
        """Get an existing remote machine by ID"""
        url = self._client._url(MachineType.REMOTE, f"vms/{id}")
        await self._client._api_client.get(url)  # Verify machine exists
        return RemoteMachine(self._client, id)
    
    def local(self) -> LocalMachine:
        """Get a local machine instance"""
        return LocalMachine(self._client)
