from __future__ import annotations

import logging
from typing import Optional, Tuple, Dict, TYPE_CHECKING

try:
    from aiohttp import web
except ImportError:
    web = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .api import KeyLightAPI

logger = logging.getLogger(__name__)


class HttpTransport:
    """HTTP transport for the KeyLight API.

    Binds to localhost only.  Routes map REST-style paths to API commands:
        GET  /api/lights            → lights.list
        POST /api/lights/toggle     → lights.toggle  (master)
        GET  /api/lights/<id>       → lights.get
        POST /api/lights/<id>/toggle → lights.toggle {id}
        PUT  /api/lights/<id>       → lights.set   {id, ...}
    """

    def __init__(
        self, api: KeyLightAPI, host: str = "127.0.0.1", port: int = 27301
    ) -> None:
        self._api = api
        self._host = host
        self._port = port
        self._runner: Optional[web.AppRunner] = None

    async def start(self) -> None:
        if web is None:
            logger.warning("aiohttp not available, HTTP transport disabled")
            return

        app = web.Application()
        app.router.add_route("*", "/api/{tail:.*}", self._handle_request)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        logger.info("HTTP API listening on http://%s:%d", self._host, self._port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_request(self, request: web.Request) -> web.Response:
        tail = request.match_info.get("tail", "").strip("/")

        # Collect params from query string and/or JSON body
        params: Dict = dict(request.query)
        if request.content_type == "application/json":
            try:
                body = await request.json()
                if isinstance(body, dict):
                    params.update(body)
            except Exception:
                pass

        command, extra_params = self._path_to_command(tail, request.method)
        params.update(extra_params)

        result = self._api.handle_request(command, params)
        status = 200 if result.get("ok") else 400
        return web.json_response(result, status=status)

    @staticmethod
    def _path_to_command(path: str, method: str) -> Tuple[str, Dict]:
        """Map a REST-style path to an API command + extra params."""
        parts = [p for p in path.split("/") if p]
        extra: Dict = {}

        if not parts or parts[0] != "lights":
            return ("", extra)

        if len(parts) == 1:
            return ("lights.list", extra)

        if len(parts) == 2:
            action = parts[1]
            if action == "toggle":
                return ("lights.toggle", extra)
            extra["id"] = action
            if method in ("PUT", "PATCH", "POST"):
                return ("lights.set", extra)
            return ("lights.get", extra)

        if len(parts) == 3:
            extra["id"] = parts[1]
            action = parts[2]
            if action == "toggle":
                return ("lights.toggle", extra)
            if action == "set":
                return ("lights.set", extra)
            return ("lights.get", extra)

        return ("", extra)
