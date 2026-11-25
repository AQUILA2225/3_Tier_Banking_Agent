from time import perf_counter
from uuid import uuid4
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Scope, Receive, Send, Message

from app.core.logging import get_logger 
from app.core.request_context import request_id_context

logger = get_logger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app 
        
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:

        # Process only HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate a unique request ID
        request_id = str(uuid4())

        # Store request ID in the current context
        token = request_id_context.set(request_id)

        # Store request ID in request state
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        # Start performance timer
        start_time = perf_counter()

        method = scope["method"]
        status_code = 500

        logger.info(
            "Request started | method=%s",
            method
        )

        async def send_wrapper(message: Message) -> None:

            nonlocal status_code

            if message["type"] == "http.response.start":

                status_code = message["status"]

                headers = MutableHeaders(scope=message)

                headers["X-Request-ID"] = request_id

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_wrapper
            )

        finally:

            duration_ms = (
                perf_counter() - start_time
            ) * 1000

            route = scope.get("route")

            route_path = getattr(
                route,
                "path",
                "<unmatched>"
            )

            logger.info(
                "Request finished | method=%s | "
                "route=%s | status=%s | duration_ms=%.2f",
                method,
                route_path,
                status_code,
                duration_ms
            )

            # Restore the previous request context
            request_id_context.reset(token)
