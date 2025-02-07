class ConnectionSession:
    """Context manager for machine connections"""
    def __init__(self, machine):
        self.machine = machine
        self.connection = None

    # For sync use
    def __enter__(self):
        self.connection = self.machine._client.connections.create(self.machine)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.machine._client.connections.delete(self.machine.id, self.connection.id)

    # For async use
    async def __aenter__(self):
        self.connection = await self.machine._client.connections.create.aio(self.machine)
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await self.machine._client.connections.delete.aio(
                self.machine.id, self.connection.id
            )
