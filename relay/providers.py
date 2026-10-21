import os
from typing import Tuple, Optional
import httpx


class ProviderError(Exception):
    """Base exception for provider failures."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ProviderRateLimitedError(ProviderError):
    def __init__(self, message: str, retry_after: Optional[str] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ProviderServerError(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class ProviderBadRequestError(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ProviderAuthError(ProviderError):
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class ProviderResponseParseError(ProviderError):
    """Raised when provider returns HTTP 200 but the response body cannot be parsed as expected JSON (P-61). Non-retryable."""
    retryable = False

    def __init__(self, message: str):
        super().__init__(message, status_code=200)


class BaseProvider:
    async def complete(self, prompt: str, **kwargs) -> Tuple[str, int, int]:
        raise NotImplementedError


class FakeProvider(BaseProvider):
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url
        raw_to = os.getenv("RELAY_PROVIDER_TIMEOUT_S", "30")
        try:
            self.timeout = float(raw_to)
        except Exception:
            self.timeout = 30.0

    async def complete(self, prompt: str, **kwargs) -> Tuple[str, int, int]:
        mode = kwargs.get("fake_mode", "ok")
        headers = {"X-Fake-Mode": mode}
        delay = kwargs.get("delay")
        if delay is not None:
            headers["X-Slow-Seconds"] = str(delay)
            if mode == "ok":
                headers["X-Fake-Mode"] = "slow_below" if float(delay) <= 5.0 else "slow_above"
        if "fake_delay" in kwargs:
            headers["X-Slow-Seconds"] = str(kwargs["fake_delay"])
        if "fake_retry_after" in kwargs:
            headers["X-Fake-Retry-After"] = str(kwargs["fake_retry_after"])
        if "fake_storm_s" in kwargs:
            headers["X-Fake-Storm-S"] = str(kwargs["fake_storm_s"])
        if "fail_pct" in kwargs:
            headers["X-Fake-Fail-Pct"] = str(kwargs["fail_pct"])

        payload = {"prompt": prompt}
        timeout = float(kwargs.get("timeout", self.timeout))

        if kwargs.get("fake_client") == "sync":
            with httpx.Client(timeout=timeout) as client:
                r = client.post(f"{self.base_url}/v1/complete", headers=headers, json=payload)
                if r.status_code == 200:
                    try:
                        data = r.json()
                    except Exception as exc:
                        raise ProviderResponseParseError(f"Provider 200 parse error: {exc}") from exc
                    return data["text"], int(data["tokens_in"]), int(data["tokens_out"])
                elif r.status_code == 429:
                    raise ProviderRateLimitedError(f"Provider 429: {r.text}", retry_after=r.headers.get("retry-after"))
                elif r.status_code == 500:
                    raise ProviderServerError(f"Provider 500: {r.text}")
                elif r.status_code == 400:
                    raise ProviderBadRequestError(f"Provider 400: {r.text}")
                elif r.status_code == 401:
                    raise ProviderAuthError(f"Provider 401: {r.text}")
                else:
                    raise ProviderError(f"Provider error {r.status_code}: {r.text}", status_code=r.status_code)

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{self.base_url}/v1/complete", headers=headers, json=payload)
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception as exc:
                    raise ProviderResponseParseError(f"Provider 200 parse error: {exc}") from exc
                return data["text"], int(data["tokens_in"]), int(data["tokens_out"])
            elif r.status_code == 429:
                raise ProviderRateLimitedError(f"Provider 429: {r.text}", retry_after=r.headers.get("retry-after"))
            elif r.status_code == 500:
                raise ProviderServerError(f"Provider 500: {r.text}")
            elif r.status_code == 400:
                raise ProviderBadRequestError(f"Provider 400: {r.text}")
            elif r.status_code == 401:
                raise ProviderAuthError(f"Provider 401: {r.text}")
            else:
                raise ProviderError(f"Provider error {r.status_code}: {r.text}", status_code=r.status_code)


class GeminiProvider(BaseProvider):
    def __init__(self, key_var: str = "GEMINI_API_KEY", model: str = "gemini-3.5-flash-lite"):
        self.key_var = key_var
        self.model = model

    async def complete(self, prompt: str, **kwargs) -> Tuple[str, int, int]:
        # Read key strictly at call-time, never at import time
        api_key = os.environ.get(self.key_var)
        if not api_key:
            raise ProviderAuthError(f"API key environment variable {self.key_var} is not set")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        timeout = float(kwargs.get("timeout", 30.0))

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                try:
                    data = r.json()
                except Exception as exc:
                    raise ProviderResponseParseError(f"Gemini 200 parse error: {exc}") from exc
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                tokens_in = int(usage.get("promptTokenCount", 0))
                tokens_out = int(usage.get("candidatesTokenCount", 0))
                return text, tokens_in, tokens_out
            elif r.status_code == 429:
                raise ProviderRateLimitedError(f"Gemini 429: {r.text}", retry_after=r.headers.get("retry-after"))
            elif r.status_code == 500:
                raise ProviderServerError(f"Gemini 500: {r.text}")
            elif r.status_code == 400:
                raise ProviderBadRequestError(f"Gemini 400: {r.text}")
            elif r.status_code == 401 or r.status_code == 403:
                raise ProviderAuthError(f"Gemini {r.status_code}: {r.text}")
            else:
                raise ProviderError(f"Gemini error {r.status_code}: {r.text}", status_code=r.status_code)
