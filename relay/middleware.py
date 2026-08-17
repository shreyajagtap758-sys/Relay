from fastapi import Request, status
from fastapi.responses import JSONResponse

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_REQUEST_BYTES = MAX_PAYLOAD_BYTES + 4 * 1024  # 266,240 bytes (260 KB total envelope)


async def limit_payload_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": "Payload exceeds 260 KB limit"},
        )
    return await call_next(request)