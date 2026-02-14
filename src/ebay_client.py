"""
eBay API client for OAuth authentication and Browse API access.
Implements token caching and response caching to minimize API calls.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from base64 import b64encode

import httpx


logger = logging.getLogger(__name__)


class EbayClient:
    """
    eBay API client implementing OAuth and Browse API access.

    Handles:
    - OAuth Client Credentials Grant (application token)
    - Token caching and auto-refresh
    - Browse API search with pagination
    - Response caching to disk
    - Affiliate link support via eBay Partner Network
    """

    # API endpoints
    TOKEN_URL_PRODUCTION = "https://api.ebay.com/identity/v1/oauth2/token"
    TOKEN_URL_SANDBOX = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_API_PRODUCTION = "https://api.ebay.com/buy/browse/v1"
    BROWSE_API_SANDBOX = "https://api.sandbox.ebay.com/buy/browse/v1"

    # OAuth scope for Browse API
    OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"

    # Marketplace IDs
    MARKETPLACE_IDS = {
        "EBAY_US": "EBAY_US",
        "EBAY_GB": "EBAY_GB",
        "EBAY_AU": "EBAY_AU",
        "EBAY_DE": "EBAY_DE",
        "EBAY_FR": "EBAY_FR",
        "EBAY_IT": "EBAY_IT",
        "EBAY_ES": "EBAY_ES",
        "EBAY_CA": "EBAY_CA",
    }

    def __init__(
        self,
        app_id: str,
        cert_id: str,
        environment: str = "PRODUCTION",
        marketplace: str = "EBAY_US",
        cache_dir: Path = Path(".cache"),
        cache_ttl_minutes: int = 15,
        affiliate_campaign_id: Optional[str] = None
    ):
        """
        Initialize eBay API client.

        Args:
            app_id: eBay App ID (Client ID)
            cert_id: eBay Cert ID (Client Secret)
            environment: "PRODUCTION" or "SANDBOX"
            marketplace: Marketplace ID (e.g., "EBAY_US")
            cache_dir: Directory for caching API responses
            cache_ttl_minutes: How long to cache responses in minutes
            affiliate_campaign_id: eBay Partner Network campaign ID (optional)
        """
        self.app_id = app_id
        self.cert_id = cert_id
        self.environment = environment.upper()
        self.marketplace = marketplace
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.affiliate_campaign_id = affiliate_campaign_id

        # Set up endpoints based on environment
        if self.environment == "PRODUCTION":
            self.token_url = self.TOKEN_URL_PRODUCTION
            self.browse_api_base = self.BROWSE_API_PRODUCTION
        else:
            self.token_url = self.TOKEN_URL_SANDBOX
            self.browse_api_base = self.BROWSE_API_SANDBOX

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Token storage
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

        # API call counter
        self.api_calls_made = 0

        logger.info(
            f"Initialized eBay client for {marketplace} in {environment} mode"
        )

    def _get_auth_header(self) -> str:
        """Generate base64-encoded authorization header for OAuth."""
        credentials = f"{self.app_id}:{self.cert_id}"
        encoded = b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _is_token_valid(self) -> bool:
        """Check if current access token is valid and not expired."""
        if not self._access_token or not self._token_expires_at:
            return False
        # Add 60 second buffer before expiration
        return datetime.now() < self._token_expires_at - timedelta(seconds=60)

    def authenticate(self) -> str:
        """
        Obtain OAuth access token using Client Credentials Grant.
        Caches token and auto-refreshes when expired.

        Returns:
            Access token string

        Raises:
            httpx.HTTPError: If authentication fails
        """
        # Return cached token if still valid
        if self._is_token_valid():
            logger.debug("Using cached OAuth token")
            return self._access_token

        logger.info("Requesting new OAuth token from eBay")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": self._get_auth_header()
        }

        data = {
            "grant_type": "client_credentials",
            "scope": self.OAUTH_SCOPE
        }

        with httpx.Client() as client:
            response = client.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info(f"OAuth token obtained, expires in {expires_in} seconds")
            return self._access_token

    def _get_cache_key(self, seller_username: str, offset: int = 0) -> str:
        """Generate cache key for API response."""
        return f"{self.marketplace}_{seller_username}_offset{offset}.json"

    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached API response if it exists and is not expired.

        Args:
            cache_key: Cache file identifier

        Returns:
            Cached response dict or None if not found/expired
        """
        cache_file = self.cache_dir / cache_key

        if not cache_file.exists():
            return None

        # Check if cache is expired
        modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - modified_time > self.cache_ttl:
            logger.debug(f"Cache expired for {cache_key}")
            return None

        logger.debug(f"Using cached response for {cache_key}")
        with open(cache_file, 'r') as f:
            return json.load(f)

    def _save_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Save API response to cache."""
        cache_file = self.cache_dir / cache_key
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"Saved response to cache: {cache_key}")

    def _search_items(
        self,
        seller_username: str,
        offset: int = 0,
        limit: int = 200,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Call Browse API search endpoint for a specific seller.

        Args:
            seller_username: eBay seller username to filter by
            offset: Pagination offset
            limit: Number of results per page (max 200)
            force_refresh: Skip cache and fetch fresh data

        Returns:
            API response dict

        Raises:
            httpx.HTTPError: If API call fails
        """
        cache_key = self._get_cache_key(seller_username, offset)

        # Check cache first unless force refresh
        if not force_refresh:
            cached = self._get_cached_response(cache_key)
            if cached:
                return cached

        # Get valid access token
        token = self.authenticate()

        # Build API request
        url = f"{self.browse_api_base}/item_summary/search"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
        }

        # Add affiliate context if configured
        if self.affiliate_campaign_id:
            headers["X-EBAY-C-ENDUSERCTX"] = (
                f"affiliateCampaignId={self.affiliate_campaign_id}"
            )

        params = {
            "filter": f"sellers:{{{seller_username}}}",
            "offset": offset,
            "limit": min(limit, 200),  # Max 200 per request
        }

        logger.info(
            f"Fetching items for seller '{seller_username}' "
            f"(offset={offset}, limit={limit})"
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            self.api_calls_made += 1

            # Save to cache
            self._save_cache(cache_key, data)

            return data

    def get_all_seller_items(
        self,
        seller_username: str,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch all active listings for a seller using pagination.

        Args:
            seller_username: eBay seller username
            force_refresh: Skip cache and fetch fresh data

        Returns:
            List of normalized item dictionaries

        Raises:
            httpx.HTTPError: If API calls fail
        """
        all_items = []
        offset = 0
        limit = 200  # Max per request
        total_items = None

        logger.info(f"Fetching all items for seller: {seller_username}")

        while True:
            try:
                response = self._search_items(
                    seller_username,
                    offset=offset,
                    limit=limit,
                    force_refresh=force_refresh
                )

                # Get total on first request
                if total_items is None:
                    total_items = response.get("total", 0)
                    logger.info(f"Seller has {total_items} total items")

                # Extract items from response
                items = response.get("itemSummaries", [])
                if not items:
                    break

                # Normalize each item
                for item in items:
                    normalized = self._normalize_item(item)
                    all_items.append(normalized)

                # Check if we've fetched all items
                offset += len(items)
                if offset >= total_items:
                    break

            except httpx.HTTPError as e:
                logger.error(f"API error at offset {offset}: {e}")
                # If we have some items and cache available, use what we have
                if all_items:
                    logger.warning("Returning partial results due to API error")
                    break
                else:
                    raise

        logger.info(f"Fetched {len(all_items)} total items")
        return all_items

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw API item response to consistent structure.

        Args:
            item: Raw item dict from Browse API

        Returns:
            Normalized item dict with all required fields
        """
        # Extract price
        price_data = item.get("price", {})
        price_value = float(price_data.get("value", 0))
        price_currency = price_data.get("currency", "USD")

        # Extract current bid for auctions
        current_bid = None
        bid_data = item.get("currentBidPrice", {})
        if bid_data:
            current_bid = {
                "value": float(bid_data.get("value", 0)),
                "currency": bid_data.get("currency", "USD")
            }

        # Extract images
        primary_image = item.get("image", {}).get("imageUrl", "")
        additional_images = []
        if "additionalImages" in item:
            additional_images = [
                img.get("imageUrl", "") for img in item["additionalImages"]
            ]

        # Extract category (use leaf category)
        category = "Uncategorized"
        if "categories" in item and item["categories"]:
            category = item["categories"][0].get("categoryName", "Uncategorized")

        # Extract shipping
        shipping_cost = None
        shipping_type = None
        if "shippingOptions" in item and item["shippingOptions"]:
            shipping = item["shippingOptions"][0]
            cost_data = shipping.get("shippingCost", {})
            if cost_data:
                shipping_cost = {
                    "value": float(cost_data.get("value", 0)),
                    "currency": cost_data.get("currency", "USD")
                }
            shipping_type = shipping.get("shippingCostType", "")

        # Determine item URL (prefer affiliate URL if available)
        item_url = item.get("itemAffiliateWebUrl") or item.get("itemWebUrl", "")

        return {
            "item_id": item.get("itemId", ""),
            "title": item.get("title", ""),
            "price": {
                "value": price_value,
                "currency": price_currency
            },
            "current_bid": current_bid,
            "primary_image": primary_image,
            "additional_images": additional_images,
            "condition": item.get("condition", ""),
            "category": category,
            "item_url": item_url,
            "shipping_cost": shipping_cost,
            "shipping_type": shipping_type,
            "location": item.get("itemLocation", {}).get("city", ""),
            "buying_options": item.get("buyingOptions", []),
            "item_end_date": item.get("itemEndDate", ""),
            "is_auction": "AUCTION" in item.get("buyingOptions", []),
            "is_buy_it_now": "FIXED_PRICE" in item.get("buyingOptions", []),
            "is_best_offer": "BEST_OFFER" in item.get("buyingOptions", []),
        }
