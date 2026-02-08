"""
Polymarket Gamma API Client.
Handles fetching market data, orderbooks, and positions.
"""
from __future__ import annotations
import asyncio
from typing import Optional, Dict, List, Any, Union
import httpx
from cachetools import TTLCache
from app.core.config import settings


class GammaAPIClient:
    """
    Async client for Polymarket Gamma API.
    Implements rate limiting and caching.
    """
    
    def __init__(self):
        self.base_url = settings.gamma_api_base_url
        self._semaphore = asyncio.Semaphore(settings.rate_limit_requests_per_second)
        
        # TTL Caches
        self._market_cache: TTLCache = TTLCache(
            maxsize=1000, 
            ttl=settings.market_cache_ttl
        )
        self._price_cache: TTLCache = TTLCache(
            maxsize=5000, 
            ttl=settings.price_cache_ttl
        )
        
        # In-memory market name mapping
        self._market_names: dict[str, str] = {}
        self._market_categories: dict[str, str] = {}
        self._market_slugs: dict[str, str] = {}
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[dict] = None
    ) -> Union[Dict[str, Any], List[Any], None]:
        """Make rate-limited async request."""
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}{endpoint}"
                try:
                    response = await client.request(method, url, params=params)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    print(f"HTTP error {e.response.status_code}: {e}")
                    return None
                except httpx.RequestError as e:
                    print(f"Request error: {e}")
                    return None
    
    async def fetch_markets(
        self, 
        limit: int = 100, 
        active: bool = True,
        closed: bool = False
    ) -> list[dict]:
        """
        Fetch market list from Gamma API.
        Results are cached for market_cache_ttl seconds.
        """
        cache_key = f"markets_{limit}_{active}_{closed}"
        
        if cache_key in self._market_cache:
            return self._market_cache[cache_key]
        
        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        
        result = await self._request("GET", "/markets", params)
        
        if result:
            self._market_cache[cache_key] = result
            # Update in-memory name mapping
            for market in result:
                condition_id = market.get("conditionId", market.get("condition_id", ""))
                if condition_id:
                    self._market_names[condition_id] = market.get("question", "Unknown Market")
                    self._market_slugs[condition_id] = market.get("slug", "")
                    # Infer category from tags or default
                    tags = market.get("tags", [])
                    if tags:
                        self._market_categories[condition_id] = self._categorize_market(tags)
                    else:
                        self._market_categories[condition_id] = "Other"
            return result
        
        return []
    
    def _categorize_market(self, tags: list[str]) -> str:
        """Categorize market based on tags."""
        tags_lower = [t.lower() for t in tags]
        
        if any(t in tags_lower for t in ["sports", "nfl", "nba", "mlb", "soccer", "football"]):
            return "Sports"
        if any(t in tags_lower for t in ["politics", "election", "trump", "biden", "congress"]):
            return "Politics"
        if any(t in tags_lower for t in ["finance", "crypto", "bitcoin", "fed", "interest"]):
            return "Finance"
        if any(t in tags_lower for t in ["entertainment", "movies", "oscars", "celebrity"]):
            return "Entertainment"
        
        return "Other"
    
    async def fetch_orderbook(self, token_id: str) -> dict:
        """
        Fetch live orderbook for a specific token.
        Used for accurate bid/ask pricing.
        """
        cache_key = f"orderbook_{token_id}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        result = await self._request("GET", f"/book", params={"token_id": token_id})
        
        if result:
            self._price_cache[cache_key] = result
            return result
        
        return {"bids": [], "asks": []}
    
    async def fetch_price(self, token_id: str) -> float:
        """
        Fetch current market price for a token.
        Uses midpoint of best bid/ask if available.
        """
        cache_key = f"price_{token_id}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        # Try to get price from prices endpoint first
        result = await self._request("GET", f"/prices", params={"token_ids": token_id})
        
        if result and token_id in result:
            price = float(result[token_id])
            self._price_cache[cache_key] = price
            return price
        
        # Fallback to orderbook midpoint
        orderbook = await self.fetch_orderbook(token_id)
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if bids and asks:
            best_bid = float(bids[0].get("price", 0))
            best_ask = float(asks[0].get("price", 1))
            price = (best_bid + best_ask) / 2
        elif bids:
            price = float(bids[0].get("price", 0.5))
        elif asks:
            price = float(asks[0].get("price", 0.5))
        else:
            price = 0.5
        
        self._price_cache[cache_key] = price
        return price
    
    async def fetch_positions(self, wallet_address: str) -> list[dict]:
        """
        Fetch all active positions for a wallet.
        Uses data-api.polymarket.com since gamma-api /positions is deprecated.
        Returns list of positions with token details.
        """
        # Use data-api.polymarket.com for positions (gamma-api /positions is 404)
        data_api_url = "https://data-api.polymarket.com/positions"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    data_api_url,
                    params={"user": wallet_address.lower()}
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"HTTP error fetching positions: {e.response.status_code}")
                return []
            except httpx.RequestError as e:
                print(f"Request error fetching positions: {e}")
                return []
    
    async def fetch_market_by_condition(self, condition_id: str) -> Optional[dict]:
        """Fetch a specific market by condition ID."""
        cache_key = f"market_{condition_id}"
        
        if cache_key in self._market_cache:
            return self._market_cache[cache_key]
        
        result = await self._request(
            "GET",
            f"/markets/{condition_id}"
        )
        
        if result:
            self._market_cache[cache_key] = result
            
            # Update in-memory mappings
            if condition_id:
                self._market_names[condition_id] = result.get("question", "Unknown Market")
                self._market_slugs[condition_id] = result.get("slug", "")
                
                tags = result.get("tags", [])
                if tags:
                    self._market_categories[condition_id] = self._categorize_market(tags)
                else:
                    self._market_categories[condition_id] = "Other"

            return result
        
        return None
    
    def get_market_name(self, condition_id: str) -> str:
        """Get cached market name."""
        return self._market_names.get(condition_id, f"Market {condition_id[:8]}...")
    
    def get_market_category(self, condition_id: str) -> str:
        """Get cached market category."""
        return self._market_categories.get(condition_id, "Other")

    def get_market_slug(self, condition_id: str) -> str:
        """Get cached market slug."""
        return self._market_slugs.get(condition_id, "")
    
    async def initialize_market_cache(self):
        """Pre-load market cache on startup."""
        await self.fetch_markets(limit=500, active=True)
        await self.fetch_markets(limit=100, active=True, closed=False)


# Global client instance
gamma_client = GammaAPIClient()
