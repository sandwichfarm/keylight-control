from __future__ import annotations

import asyncio
import json
import os
import logging
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .api import KeyLightAPI

logger = logging.getLogger(__name__)


class UnixSocketTransport:
    """Unix socket transport for the KeyLight API.

    Protocol: newline-delimited JSON.
    Request:  {"command": "lights.toggle", "params": {}}
    Response: {"ok": true, ...}
    """

    def __init__(self, api: KeyLightAPI, socket_path: Optional[str] = None) -> None:
        self._api = api
        self._socket_path = socket_path or self._default_socket_path()
        self._server: Optional[asyncio.AbstractServer] = None

    @staticmethod
    def _default_socket_path() -> str:
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if runtime_dir:
            return os.path.join(runtime_dir, "keylight-control.sock")
        return "/tmp/keylight-control.sock"

    async def start(self) -> None:
        # Remove stale socket file
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass

        self._server = await asyncio.start_unix_server(
            self._handle_client, path=self._socket_path
        )
        os.chmod(self._socket_path, 0o600)
        logger.info("Unix socket API listening on %s", self._socket_path)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        try:
            os.unlink(self._socket_path)
        except FileNotFoundError:
            pass

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    request = json.loads(line.decode("utf-8").strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    response = {"ok": False, "error": "Invalid JSON"}
                    writer.write((json.dumps(response) + "\n").encode("utf-8"))
                    await writer.drain()
                    continue

                command = request.get("command", "")
                params = request.get("params", {})
                response = self._api.handle_request(command, params)
                writer.write((json.dumps(response) + "\n").encode("utf-8"))
                await writer.drain()
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    @property
    def socket_path(self) -> str:
        return self._socket_path
