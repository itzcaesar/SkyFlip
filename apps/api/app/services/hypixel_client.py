import asyncio
import logging
from typing import Any

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)


class HypixelAPIError(RuntimeError):
    pass


class HypixelClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = client

    async def fetch_bazaar(self) -> dict[str, Any]:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url=str(self.settings.hypixel_base_url).rstrip("/"),
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers={"User-Agent": "SkyFlip/0.1 (+market-intelligence)"},
        )
        if self.settings.hypixel_api_key:
            client.headers["API-Key"] = self.settings.hypixel_api_key
        try:
            for attempt in range(self.settings.bazaar_max_retries):
                try:
                    response = await client.get("/v2/skyblock/bazaar")
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", "2"))
                        await asyncio.sleep(min(max(retry_after, 1), 30))
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict) or payload.get("success") is not True:
                        raise HypixelAPIError("Hypixel returned an unsuccessful Bazaar response.")
                    products = payload.get("products")
                    if not isinstance(products, dict):
                        raise HypixelAPIError("Hypixel Bazaar response did not contain products.")
                    return payload
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == self.settings.bazaar_max_retries - 1:
                        raise HypixelAPIError(
                            "Hypixel Bazaar request timed out or failed."
                        ) from exc
                    await asyncio.sleep(2**attempt)
                except httpx.HTTPStatusError as exc:
                    if (
                        exc.response.status_code >= 500
                        and attempt < self.settings.bazaar_max_retries - 1
                    ):
                        await asyncio.sleep(2**attempt)
                        continue
                    raise HypixelAPIError(
                        f"Hypixel Bazaar request returned HTTP {exc.response.status_code}."
                    ) from exc
            raise HypixelAPIError("Hypixel Bazaar request exhausted retries.")
        finally:
            if owns_client:
                await client.aclose()
