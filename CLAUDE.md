# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based static site generator that pulls a seller's active eBay listings via the Browse API, organizes them by category, and renders a clean, responsive HTML catalog site. The system is multi-tenant and configurable via YAML config files so it can be deployed for any eBay seller without code changes.

**Output**: Static HTML that can be served from S3, CloudFront, Nginx, or any static host.

## Project Structure

```
ebay-catalog/
├── config/
│   ├── config.example.yaml        # Template config with documentation
│   └── sellers/                   # Per-seller config overrides (optional)
├── src/
│   ├── ebay_client.py             # eBay API OAuth + Browse API wrapper
│   ├── catalog_builder.py         # Fetches listings, organizes by category
│   ├── site_generator.py          # Renders Jinja2 templates to static HTML
│   └── deploy.py                  # Optional: push to S3 or rsync to server
├── templates/
│   ├── base.html                  # Base layout with nav, footer
│   ├── index.html                 # Landing page with featured/recent items
│   ├── category.html              # Category listing page
│   └── item.html                  # Individual item detail page (optional)
├── static/
│   ├── css/styles.css             # Clean, modern responsive CSS
│   └── images/                    # Seller logo, favicon, etc.
├── output/                        # Generated static site lands here
├── build.py                       # Main entry point — orchestrates everything
└── requirements.txt
```

## Build and Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Build the catalog site (once implemented)
python build.py

# Force refresh from API, ignoring cache
python build.py --force-refresh

# Use custom config file
python build.py --config path/to/config.yaml

# Dry run (fetch and build but don't write output)
python build.py --dry-run

# Build without deploying
python build.py --no-deploy
```

## Architecture and Design Principles

### Data Flow
1. **eBay Client** (`ebay_client.py`): Authenticates via OAuth, fetches all seller listings from Browse API, caches responses
2. **Catalog Builder** (`catalog_builder.py`): Groups items by category, sorts, filters, builds data structure
3. **Site Generator** (`site_generator.py`): Renders Jinja2 templates to static HTML using catalog data
4. **Deploy** (`deploy.py`): Optionally pushes output to S3 or rsync to server

### eBay API Integration

**Authentication**: OAuth Client Credentials Grant (application token)
- Token endpoint: `https://api.ebay.com/identity/v1/oauth2/token`
- Scope: `https://api.ebay.com/oauth/api_scope`
- Tokens last 2 hours; implement auto-refresh with caching

**Browse API**: `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
- Filter by seller: `filter=sellers:{seller_username}`
- Pagination: use `offset` and `limit` params (max `limit=200`)
- Rate limit: 5,000 calls/day on individual tier

**Key fields to extract**:
- `itemId`, `title`, `price`, `image.imageUrl`, `additionalImages`
- `condition`, `categories`, `itemWebUrl`, `shippingOptions`
- `itemLocation`, `buyingOptions`, `currentBidPrice`, `itemEndDate`
- Use `itemAffiliateWebUrl` if affiliate tracking is configured

### Caching Strategy
- Cache raw API responses as JSON files in `.cache/` directory
- Configurable TTL (default 15 minutes) to avoid unnecessary API calls
- If cache valid, skip API call entirely
- On API failure, fall back to cached data if available
- Log API call count per run

### Site Generation

**Design requirements**:
- Mobile-first responsive design (CSS Grid, no frameworks)
- Clean card-based layout for items
- Minimal CSS, vanilla JS only (lazy loading, countdown timers)
- Semantic HTML, proper accessibility (alt tags, contrast)

**Pages to generate**:
1. `index.html` — Landing page with category nav and recent items
2. `category/{slug}.html` — One page per category with item grid
3. `sitemap.xml` — For SEO (if enabled in config)

**Item card components**:
- Product image (lazy-loaded)
- Title (max 2 lines, CSS truncated)
- Price (show "Current Bid: $X" for auctions)
- Condition badge (colored pill: green=New, blue=Like New, gray=Used)
- Shipping cost or "Free Shipping" badge
- Buying format indicator (auction, best offer)
- "View on eBay" CTA button (opens in new tab)

### Atomic Output Generation
- Render to a temporary directory first
- Only swap to `output/` on successful completion
- Never leave a broken/partial output directory
- Either produce a complete site or don't modify output

### Multi-Tenant Configuration
All seller-specific settings live in `config.yaml`:
- eBay API credentials
- Seller username and display info
- Site branding (title, tagline, logo)
- Category ordering and visibility
- Build and deploy options
- Affiliate campaign ID for eBay Partner Network

## Python Code Standards

- Use type hints on all functions
- Include docstrings for modules, classes, and functions
- Use `httpx` for HTTP calls (async-capable)
- Use `pyyaml` for config parsing
- Use `jinja2` for templating
- Use `pathlib` for all file paths
- Pin all versions in `requirements.txt`
- Implement proper error handling with logging

## eBay Affiliate Integration

If `affiliate_campaign_id` is set in config:
- Use `X-EBAY-C-ENDUSERCTX` header with `affiliateCampaignId` in API calls
- API returns `itemAffiliateWebUrl` with tracking already included
- Use affiliate URL instead of `itemWebUrl` when available

## Category Organization

**Sorting**:
- Use `categories.custom_order` from config if defined, otherwise alphabetical
- Within categories: auction items ending soonest first, then newest listings
- Filter out categories in `categories.hidden`

**Data structure**:
```python
{
    "seller": { ... },
    "categories": [
        {
            "name": "Electronics",
            "slug": "electronics",
            "item_count": 15,
            "items": [ ... ]
        }
    ],
    "total_items": 47,
    "generated_at": "2026-02-13T10:30:00Z"
}
```

## Development Notes

- This is a static site generator — no database, no server runtime, no user auth
- The output is purely static HTML/CSS/JS that can be hosted anywhere
- No JavaScript frameworks (React, Vue) or CSS frameworks (Bootstrap, Tailwind)
- Designed to be run on a cron job (e.g., every 15 minutes) to keep catalog fresh
- Config is YAML-based for easy multi-seller deployment without code changes

## Reference Documentation

See `docs/ebay-catalog-builder-prompt.md` for the complete project specification including detailed requirements, API integration details, and configuration schema.
