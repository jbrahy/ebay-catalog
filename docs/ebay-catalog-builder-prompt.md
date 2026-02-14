# Claude Code Prompt: eBay Seller Catalog — Static Site Generator

## Project Overview

Build a Python-based static site generator that pulls a seller's active eBay listings via the Browse API, organizes them by category, and renders a clean, responsive HTML catalog site. The system must be multi-tenant — configurable via a YAML config file so it can be deployed for any eBay seller without code changes. The output is static HTML that can be served from S3, CloudFront, Nginx, or any static host.

## Architecture

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
│   ├── css/
│   │   └── styles.css             # Clean, modern responsive CSS
│   └── images/                    # Seller logo, favicon, etc.
├── output/                        # Generated static site lands here
├── build.py                       # Main entry point — orchestrates everything
├── requirements.txt
└── README.md
```

## Config File: `config.yaml`

Design the YAML config to support these fields:

```yaml
# eBay API Credentials
ebay:
  app_id: "YOUR_APP_ID"                    # Client ID from developer.ebay.com
  cert_id: "YOUR_CERT_ID"                  # Client Secret
  environment: "PRODUCTION"                 # PRODUCTION or SANDBOX
  marketplace: "EBAY_US"                    # EBAY_US, EBAY_UK, EBAY_DE, etc.

# Seller Configuration
seller:
  username: "seller_username"               # eBay seller username
  display_name: "John's Deals"             # Brand name shown on site
  tagline: "Quality finds, great prices"   # Subtitle/tagline
  logo: "images/logo.png"                  # Optional logo path
  contact_email: ""                        # Optional contact

# Site Configuration
site:
  title: "John's Deals"
  base_url: "https://johnsdeals.com"       # For canonical URLs and sitemap
  items_per_page: 24                       # Pagination limit per category page
  show_price: true
  show_shipping: true
  show_condition: true
  show_time_remaining: true                # For auction items
  affiliate_campaign_id: ""                # eBay Partner Network campaign ID (optional)
  
# Category Mapping (optional overrides)
# Map eBay category IDs to custom display names and sort order
categories:
  custom_order:                            # Controls nav/display order
    - "Electronics"
    - "Collectibles"
    - "Home & Garden"
  # Optionally hide categories:
  hidden: []

# Build Configuration  
build:
  output_dir: "output"
  cache_dir: ".cache"
  cache_ttl_minutes: 15                    # How long to cache API responses
  download_images: false                   # If true, download images locally vs hotlink
  generate_sitemap: true

# Deploy Configuration (optional)
deploy:
  method: "none"                           # none, s3, rsync
  s3_bucket: ""
  s3_region: "us-east-1"
  rsync_target: ""
```

## eBay API Integration (`ebay_client.py`)

### OAuth Implementation
- Use eBay's OAuth Client Credentials Grant (application token) for the Browse API — no user auth required since we're only reading public listings.
- Token endpoint: `https://api.ebay.com/identity/v1/oauth2/token`
- Cache the access token and auto-refresh when expired (tokens last 2 hours).
- Scope needed: `https://api.ebay.com/oauth/api_scope`

### Browse API Calls
- Use the **Browse API `search`** method: `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
- Filter by seller: use the `filter` param with `sellers:{seller_username}`
- Pull ALL active listings using pagination (`offset` and `limit` params, max `limit=200`)
- For each item, extract and normalize:
  - `itemId` — used for building the eBay purchase URL
  - `title`
  - `price` (value + currency)
  - `image.imageUrl` — primary image
  - `additionalImages` — gallery images if available
  - `condition` — New, Used, etc.
  - `categories` — extract the leaf category name for grouping
  - `itemWebUrl` — direct link to purchase on eBay
  - `shippingOptions` — shipping cost or "Free Shipping"
  - `itemLocation` — seller location
  - `buyingOptions` — FIXED_PRICE, AUCTION, or BEST_OFFER
  - `currentBidPrice` — for auction items
  - `itemEndDate` — for auction countdown

### Affiliate Link Support
If `affiliate_campaign_id` is set in config, append eBay Partner Network tracking params to all outbound `itemWebUrl` links using the `X-EBAY-C-ENDUSERCTX` header with `affiliateCampaignId` during the API call. The API will return `itemAffiliateWebUrl` which already includes tracking — use that instead of `itemWebUrl` when available.

### Rate Limiting & Caching
- Cache raw API responses to disk (JSON files in `.cache/` directory) with configurable TTL.
- Respect eBay's rate limits (5,000 calls/day for Browse API on individual tier).
- If a cached response exists and is within TTL, skip the API call entirely.
- Log the number of API calls made per run.

## Catalog Builder (`catalog_builder.py`)

- Consume the normalized listing data from `ebay_client.py`.
- Group items by their eBay leaf category name.
- Sort categories: use `custom_order` from config if defined, otherwise alphabetical.
- Within each category, sort items by: auction ending soonest first, then by listing date (newest first).
- Filter out any categories listed in `categories.hidden`.
- Build a data structure like:

```python
{
    "seller": { ... },
    "categories": [
        {
            "name": "Electronics",
            "slug": "electronics",
            "item_count": 15,
            "items": [ ... ]
        },
        ...
    ],
    "total_items": 47,
    "generated_at": "2026-02-13T10:30:00Z"
}
```

## Site Generator (`site_generator.py`)

### Templates (Jinja2)

**Design Requirements:**
- Mobile-first responsive design. Looks great on phones since many buyers browse on mobile.
- Clean, modern card-based grid layout for items (CSS Grid, not Bootstrap or any framework).
- Color scheme: use a neutral base (white/light gray) with a configurable accent color in the config.
- Fast-loading: minimal CSS, no JavaScript frameworks. Vanilla JS only where needed (e.g., image lazy loading, auction countdown timer).
- Accessible: proper semantic HTML, alt tags on images, readable contrast ratios.

**Pages to Generate:**

1. **`index.html`** — Landing page
   - Hero section with seller display name, tagline, logo
   - Category navigation (cards or pills linking to category pages)
   - "Recently Listed" section showing the newest 8 items across all categories
   - Total item count
   - Footer with "Last updated" timestamp and optional contact

2. **`category/{slug}.html`** — One page per category
   - Breadcrumb: Home > Category Name
   - Grid of item cards
   - Each card shows: image, title (truncated to 2 lines), price, condition badge, shipping info
   - "Buy on eBay" button/link on each card — opens in new tab
   - Auction items show time remaining with a small countdown or "Ending Soon" badge
   - Pagination if items exceed `items_per_page`

3. **`sitemap.xml`** — For SEO (if enabled in config)

**Item Cards Must Include:**
- Product image (lazy-loaded)
- Title (max 2 lines, CSS truncated)
- Price (bold, prominent) — show "Current Bid: $X" for auction items
- Condition badge (small colored pill: green=New, blue=Like New, gray=Used)
- Shipping cost or "Free Shipping" badge (highlighted in green)
- Buying format indicator if auction or best offer
- "View on eBay" CTA button — styled prominently, opens `itemWebUrl` or `itemAffiliateWebUrl` in new tab

## Build Script (`build.py`)

Main entry point that:
1. Loads and validates config
2. Initializes eBay client, authenticates
3. Fetches all listings (with caching)
4. Builds the categorized catalog data structure
5. Renders all templates to `output/` directory
6. Copies static assets to `output/static/`
7. Optionally runs deploy step
8. Prints summary: items fetched, categories, pages generated, time elapsed

Support CLI args:
- `--config path/to/config.yaml` (default: `config/config.yaml`)
- `--force-refresh` — ignore cache, pull fresh from API
- `--no-deploy` — skip deploy step even if configured
- `--dry-run` — fetch and build but don't write output

## Additional Requirements

- All Python code should use type hints and docstrings.
- Use `httpx` for HTTP calls (async-capable for future optimization).
- Use `pyyaml` for config parsing.
- Use `jinja2` for templating.
- Use `pathlib` for all file paths.
- Include proper error handling: if the API fails, log the error and fall back to cached data if available. Never crash and leave a broken output directory — either produce a complete site or don't modify output.
- Write the output atomically: render to a temp directory first, then swap it into `output/` only on success.
- The `README.md` should include: setup instructions, how to get eBay API keys (step by step), config explanation, cron job example for auto-refresh, and deployment options.
- Include a `requirements.txt` with pinned versions.

## Cron Example for README

```bash
# Refresh catalog every 15 minutes
*/15 * * * * cd /opt/ebay-catalog && python build.py >> /var/log/ebay-catalog.log 2>&1
```

## Do NOT Include
- No JavaScript frameworks (React, Vue, etc.)
- No CSS frameworks (Bootstrap, Tailwind CDN)
- No database — this is file-based
- No user authentication or admin panel
- No server-side runtime — output must be purely static HTML/CSS/JS
