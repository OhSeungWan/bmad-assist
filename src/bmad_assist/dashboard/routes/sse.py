"""SSE (Server-Sent Events) route handlers.

Provides the live output streaming endpoint.
"""

from collections.abc import AsyncGenerator

from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from starlette.routing import Route


async def sse_output(request: Request) -> Response:
    """GET /sse/output - SSE stream for live output.

    Returns Server-Sent Events stream with:
    - output: bmad-assist stdout/stderr lines
    - status: General status updates
    - heartbeat: Keep-alive pings
    """
    server = request.app.state.server

    async def event_generator() -> AsyncGenerator[str, None]:
        async for message in server.sse_broadcaster.subscribe():
            yield message

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


routes = [
    Route("/sse/output", sse_output, methods=["GET"]),
]
