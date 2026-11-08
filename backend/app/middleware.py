from collections import defaultdict, deque
from urllib.parse import urlsplit
import hmac
import time

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.services.auth import CSRF_COOKIE, verify_csrf_token

LIMIT = 100
WINDOW = 60
_buckets: dict[str, deque[float]] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else 'unknown'
        is_auth = (
            request.url.path.startswith('/api/v1/auth/')
            and request.method not in {'GET', 'HEAD', 'OPTIONS'}
        )
        limit, window = (10, 15 * 60) if is_auth else (LIMIT, WINDOW)
        key = f'{ip}:auth' if is_auth else ip
        now = time.time()
        bucket = _buckets[key]
        while bucket and bucket[0] < now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return JSONResponse(status_code=429, content={'detail': 'RATE_LIMITED'})
        bucket.append(now)

        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and request.url.path.startswith('/api/v1/'):
            if settings.app_env.lower() not in {'development', 'test'}:
                origin = request.headers.get('origin', '')
                frontend = urlsplit(settings.frontend_url)
                expected_origin = f'{frontend.scheme}://{frontend.netloc}'
                if not origin or origin != expected_origin:
                    return JSONResponse(status_code=403, content={'detail': 'INVALID_ORIGIN'})
            cookie_token = request.cookies.get(CSRF_COOKIE, '')
            header_token = request.headers.get('x-csrf-token', '')
            if (
                not cookie_token
                or not header_token
                or not hmac.compare_digest(cookie_token, header_token)
                or not verify_csrf_token(cookie_token)
            ):
                return JSONResponse(status_code=403, content={'detail': 'CSRF_VALIDATION_FAILED'})
        return await call_next(request)
