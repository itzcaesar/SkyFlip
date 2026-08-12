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

    def _make_client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            base_url=str(self.settings.hypixel_base_url).rstrip("/"),
            timeout=httpx.Timeout(20.0, connect=5.0),
            headers={"User-Agent": "SkyFlip/0.1 (+market-intelligence)"},
        )
        if self.settings.hypixel_api_key:
            client.headers["API-Key"] = self.settings.hypixel_api_key
        return client

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, int] | None = None,
        resource_name: str,
    ) -> dict[str, Any]:
        for attempt in range(self.settings.bazaar_max_retries):
            try:
                response = await client.get(path, params=params)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", "2"))
                    await asyncio.sleep(min(max(retry_after, 1), 30))
                    continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or payload.get("success") is not True:
                    raise HypixelAPIError(
                        f"Hypixel returned an unsuccessful {resource_name} response."
                    )
                return payload
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self.settings.bazaar_max_retries - 1:
                    raise HypixelAPIError(
                        f"Hypixel {resource_name} request timed out or failed."
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
                    f"Hypixel {resource_name} request returned HTTP {exc.response.status_code}."
                ) from exc
        raise HypixelAPIError(f"Hypixel {resource_name} request exhausted retries.")

    async def fetch_bazaar(self) -> dict[str, Any]:
        owns_client = self._client is None
        client = self._client or self._make_client()
        try:
            payload = await self._request_json(
                client, "/v2/skyblock/bazaar", resource_name="Bazaar"
            )
            products = payload.get("products")
            if not isinstance(products, dict):
                raise HypixelAPIError("Hypixel Bazaar response did not contain products.")
            return payload
        finally:
            if owns_client:
                await client.aclose()

    async def fetch_auctions(self) -> dict[str, Any]:
        """Fetch the public Auction House pages into one normalized payload."""

        owns_client = self._client is None
        client = self._client or self._make_client()
        try:
            first_page = await self._request_json(
                client,
                "/v2/skyblock/auctions",
                params={"page": 0},
                resource_name="Auction House",
            )
            try:
                total_pages = max(1, int(first_page.get("totalPages", 1)))
            except (TypeError, ValueError):
                total_pages = 1
            page_limit = min(total_pages, self.settings.auction_max_pages)
            auctions = list(first_page.get("auctions", []))
            for page in range(1, page_limit):
                page_payload = await self._request_json(
                    client,
                    "/v2/skyblock/auctions",
                    params={"page": page},
                    resource_name="Auction House",
                )
                page_auctions = page_payload.get("auctions", [])
                if isinstance(page_auctions, list):
                    auctions.extend(page_auctions)
            if total_pages > page_limit:
                logger.warning(
                    "auction_page_limit_reached total_pages=%d page_limit=%d",
                    total_pages,
                    page_limit,
                )
            return {
                "success": True,
                "lastUpdated": first_page.get("lastUpdated"),
                "totalPages": total_pages,
                "pageCount": page_limit,
                "totalAuctions": first_page.get("totalAuctions", len(auctions)),
                "auctions": auctions,
            }
        finally:
            if owns_client:
                await client.aclose()
