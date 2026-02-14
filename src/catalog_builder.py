"""
Catalog builder that organizes eBay items by category and applies sorting/filtering.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


logger = logging.getLogger(__name__)


class CatalogBuilder:
    """
    Organizes raw item data into a structured catalog with categories.

    Handles:
    - Grouping items by category
    - Category sorting (custom order or alphabetical)
    - Item sorting within categories (auctions first, then newest)
    - Category filtering (hide specific categories)
    """

    def __init__(
        self,
        custom_category_order: List[str] = None,
        hidden_categories: List[str] = None
    ):
        """
        Initialize catalog builder.

        Args:
            custom_category_order: List of category names in desired display order
            hidden_categories: List of category names to exclude from catalog
        """
        self.custom_category_order = custom_category_order or []
        self.hidden_categories = set(hidden_categories or [])

    def build_catalog(
        self,
        items: List[Dict[str, Any]],
        seller_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build complete catalog data structure from items.

        Args:
            items: List of normalized item dicts from EbayClient
            seller_info: Seller metadata (display_name, tagline, etc.)

        Returns:
            Catalog dict with categories, items, and metadata
        """
        logger.info(f"Building catalog from {len(items)} items")

        # Group items by category
        category_map = self._group_by_category(items)

        # Filter hidden categories
        category_map = {
            name: items
            for name, items in category_map.items()
            if name not in self.hidden_categories
        }

        # Sort items within each category
        for category_name, category_items in category_map.items():
            category_items.sort(key=self._item_sort_key)

        # Build category list with metadata
        categories = []
        for category_name in self._get_category_order(category_map.keys()):
            category_items = category_map[category_name]
            categories.append({
                "name": category_name,
                "slug": self._slugify(category_name),
                "item_count": len(category_items),
                "items": category_items
            })

        catalog = {
            "seller": seller_info,
            "categories": categories,
            "total_items": len(items),
            "generated_at": datetime.utcnow().isoformat() + "Z"
        }

        logger.info(
            f"Catalog built with {len(categories)} categories, "
            f"{len(items)} total items"
        )

        return catalog

    def _group_by_category(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group items by their category name.

        Args:
            items: List of normalized item dicts

        Returns:
            Dict mapping category name to list of items
        """
        category_map = defaultdict(list)

        for item in items:
            category = item.get("category", "Uncategorized")
            category_map[category].append(item)

        return dict(category_map)

    def _get_category_order(self, category_names: List[str]) -> List[str]:
        """
        Determine final category display order.

        Uses custom_category_order if defined, otherwise alphabetical.
        Categories in custom order appear first, then remaining alphabetically.

        Args:
            category_names: All category names from items

        Returns:
            Ordered list of category names
        """
        if not self.custom_category_order:
            # Pure alphabetical
            return sorted(category_names)

        # Custom order first, then remaining alphabetically
        ordered = []
        remaining = set(category_names)

        # Add categories in custom order
        for cat_name in self.custom_category_order:
            if cat_name in remaining:
                ordered.append(cat_name)
                remaining.remove(cat_name)

        # Add remaining categories alphabetically
        ordered.extend(sorted(remaining))

        return ordered

    def _item_sort_key(self, item: Dict[str, Any]) -> tuple:
        """
        Generate sort key for items within a category.

        Sort order:
        1. Auction items ending soonest first (if is_auction)
        2. Items without end dates (buy it now) by newest first
        3. Secondary sort by title for consistency

        Args:
            item: Normalized item dict

        Returns:
            Tuple for sorting
        """
        is_auction = item.get("is_auction", False)
        end_date = item.get("item_end_date", "")
        title = item.get("title", "")

        if is_auction and end_date:
            # Auctions sort by end date ascending (soonest first)
            # Return negative to ensure auctions come before non-auctions
            return (0, end_date, title)
        else:
            # Non-auctions sort by title (or could use listing date if available)
            # Put them after auctions
            return (1, "", title)

    def _slugify(self, text: str) -> str:
        """
        Convert category name to URL-safe slug.

        Args:
            text: Category name

        Returns:
            Slugified string (lowercase, spaces to hyphens, only alphanumeric)
        """
        # Convert to lowercase
        slug = text.lower()

        # Replace spaces with hyphens
        slug = slug.replace(" ", "-")

        # Remove special characters (keep only alphanumeric and hyphens)
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        # Remove consecutive hyphens
        while "--" in slug:
            slug = slug.replace("--", "-")

        # Strip leading/trailing hyphens
        slug = slug.strip("-")

        return slug
