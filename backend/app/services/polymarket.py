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
                    
                    # Extract correct slug for linking (Event Slug > Market Slug)
                    events = market.get("events", [])
                    if events and isinstance(events, list) and len(events) > 0:
                        slug = events[0].get("slug")
                        if not slug:
                            slug = market.get("slug", "")
                    else:
                        slug = market.get("slug", "")
                    
                    self._market_slugs[condition_id] = slug
                    
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
        
        # Use query param 'condition_ids' which returns a list
        result = None
        result_list = await self._request(
            "GET",
            "/markets",
            params={"condition_ids": condition_id}
        )
        
        if result_list and isinstance(result_list, list) and len(result_list) > 0:
            result = result_list[0]
        
        if result:
            self._market_cache[cache_key] = result
            
            # Update in-memory mappings
            condition_id = result.get("conditionId", result.get("condition_id", ""))
            if condition_id:
                self._market_names[condition_id] = result.get("question", "Unknown Market")
                
                # Extract correct slug
                events = result.get("events", [])
                if events and isinstance(events, list) and len(events) > 0:
                    slug = events[0].get("slug")
                    if not slug:
                        slug = result.get("slug", "")
                else:
                    slug = result.get("slug", "")
                
                self._market_slugs[condition_id] = slug
                
                # Categorize
                tags = result.get("tags", [])
                if tags:
                    self._market_categories[condition_id] = self._categorize_market(tags)
                else:
                    self._market_categories[condition_id] = "Other"
            
            return result
    
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

    # =========================================================================
    # Data API – Trade Activity (for Freshness Scoring)
    # =========================================================================

    async def fetch_activity(
        self, wallet_address: str, limit: int = 500
    ) -> list[dict]:
        """
        Fetch trade activity for a wallet from the Data API.
        Returns list of trades with timestamps.
        """
        cache_key = f"activity_{wallet_address.lower()}"

        if cache_key in self._market_cache:
            return self._market_cache[cache_key]

        data_api_url = "https://data-api.polymarket.com/activity"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    data_api_url,
                    params={
                        "user": wallet_address.lower(),
                        "limit": str(limit),
                    },
                )
                response.raise_for_status()
                result = response.json()
                self._market_cache[cache_key] = result
                return result
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                print(f"Activity fetch error for {wallet_address[:10]}...: {e}")
                return []

    async def fetch_earliest_trades(
        self, wallet_address: str
    ) -> Dict[str, int]:
        """
        Get the earliest trade timestamp per asset for a wallet.

        Returns:
            Dict mapping asset (token_id) -> earliest Unix timestamp.
        """
        trades = await self.fetch_activity(wallet_address, limit=500)

        earliest: Dict[str, int] = {}
        for trade in trades:
            asset = trade.get("asset", "")
            ts = trade.get("timestamp", 0)
            if asset and ts:
                if asset not in earliest or ts < earliest[asset]:
                    earliest[asset] = ts

        return earliest

    # =========================================================================
    # CLOB API – Price History (for Momentum Scoring)
    # =========================================================================
    
    CLOB_BASE_URL = "https://clob.polymarket.com"
    
    async def fetch_price_history(self, token_id: str, interval: str = "1w") -> Optional[List[dict]]:
        """
        Fetch price history from the CLOB API.
        
        Args:
            token_id: The CLOB token ID (YES or NO token).
            interval: Time window – '1h', '6h', '1d', '1w', 'max'.
        
        Returns:
            List of {t: timestamp, p: price} or None on error.
        """
        cache_key = f"price_hist_{token_id}_{interval}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    response = await client.get(
                        f"{self.CLOB_BASE_URL}/prices-history",
                        params={
                            "market": token_id,
                            "interval": interval,
                            "fidelity": 60,  # 1-hour resolution
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    history = data.get("history", [])
                    self._price_cache[cache_key] = history
                    return history
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    print(f"CLOB price history error for {token_id[:12]}...: {e}")
                    return None
    
    async def get_7d_average_price(self, token_id: str) -> Optional[float]:
        """
        Get the 7-day average price for a token from the CLOB API.
        
        Returns:
            Average price over the last week, or None if no data.
        """
        history = await self.fetch_price_history(token_id, interval="1w")
        
        if not history:
            return None
        
        prices = [float(point.get("p", 0)) for point in history if point.get("p") is not None]
        
        if not prices:
            return None
        
        return sum(prices) / len(prices)
    
    async def get_7d_averages_batch(self, token_ids: List[str]) -> Dict[str, float]:
        """
        Batch fetch 7-day averages for multiple tokens.
        Returns mapping of token_id -> average_price.
        """
        results: Dict[str, float] = {}
        
        # Run requests concurrently (respecting semaphore rate limit)
        tasks = [self.get_7d_average_price(tid) for tid in token_ids]
        averages = await asyncio.gather(*tasks, return_exceptions=True)
        
        for token_id, avg in zip(token_ids, averages):
            if isinstance(avg, float) and avg > 0:
                results[token_id] = avg
        
        return results


# Global client instance
gamma_client = GammaAPIClient()
