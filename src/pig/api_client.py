import os
from typing import Any, Dict, Optional, Union

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client import ClientResponse
from aiohttp_retry import ExponentialRetry, RetryClient

try:
    from importlib.metadata import version
    __version__ = version("pig-python")
except Exception:
    __version__ = "unknown"

# UI URL will be determined by environment
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

class APIClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _session(self) -> RetryClient:
        retry_options = ExponentialRetry(
            attempts=float("inf"),  # Infinite retries
            start_timeout=0.1,
            max_timeout=60,  # Max delay of 60 seconds between retries
            factor=1.3,  # Exponential backoff factor
            statuses={503},  # Only retry on 503 status
            retry_all_server_errors=False,
        )

        session = ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Client-Language": "python",
                "X-Client-Version": __version__,
            },
            timeout=ClientTimeout(total=900),  # 15 minute total timeout
        )

        retry_client = RetryClient(client_session=session, retry_options=retry_options)
        return retry_client

    async def _handle_response(self, response: ClientResponse, expect_json: bool = True) -> Union[Dict[str, Any], bytes]:
        try:
            if response.status >= 400:
                error_body = await response.text()
                try:
                    error_json = await response.json()
                    error_msg = error_json.get('detail', error_body)
                except Exception:
                    error_msg = error_body
                raise APIError(response.status, error_msg)
                
            # Handle successful responses
            if not response.content or response.content_length == 0:
                return {}

            if expect_json:
                if not response.content_type.startswith("application/json"):
                    raise APIError(response.status, f"Expected JSON response but got content-type: {response.content_type}")
                return await response.json() if response.content else {}

            body = await response.read()
            return body

        except APIError:
            raise
        except Exception as e:
            raise APIError(response.status, str(e)) from e

    async def get(self, url: str, headers: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        print("GET", url)
        async with self._session() as session:
            async with session.get(url, headers=headers) as response:
                return await self._handle_response(response, expect_json)

    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        print("POST", url)
        async with self._session() as session:
            async with session.post(url, json=data, headers=headers) as response:
                return await self._handle_response(response, expect_json)

    async def put(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        print("PUT", url)
        async with self._session() as session:
            async with session.put(url, json=data, headers=headers) as response:
                return await self._handle_response(response, expect_json)

    async def delete(self, url: str, headers: Optional[Dict[str, Any]] = None, expect_json: bool = True) -> Union[Dict[str, Any], ClientResponse]:
        print("DELETE", url)
        async with self._session() as session:
            async with session.delete(url, headers=headers) as response:
                return await self._handle_response(response, expect_json)
