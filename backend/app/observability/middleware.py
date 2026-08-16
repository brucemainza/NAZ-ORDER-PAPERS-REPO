from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders

from app.observability.logging import request_id_context

logger = logging.getLogger("app.observability.http")
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RequestObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        supplied = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = supplied if VALID_REQUEST_ID.fullmatch(supplied) else str(uuid4())
        token = request_id_context.set(request_id)
        method = scope.get("method", "UNKNOWN")
        raw_path = scope.get("path", "/")
        status_code = 500
        started = perf_counter()

        async def send_with_request_id(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration = perf_counter() - started
            route_object = scope.get("route")
            route = getattr(route_object, "path", "unmatched")
            logger.info(
                "request completed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": raw_path,
                    "route": route,
                    "status": status_code,
                    "duration_ms": round(duration * 1000, 3),
                },
            )
            request_id_context.reset(token)
