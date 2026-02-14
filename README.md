# eBay Catalog Builder

A Python-based static site generator that creates a clean, responsive catalog website from any eBay seller's active listings. Perfect for sellers who want a standalone website showcasing their inventory without building custom integrations.

## Quick Start

```bash
git clone https://github.com/jbrahy/ebay-catalog.git
cd ebay-catalog
python3 -m venv venv && venv/bin/pip install -r requirements.txt

# Try demo mode first (no eBay account needed!)
./catalog-build.sh --demo
open output/index.html  # View the demo catalog

# For real eBay data:
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your eBay API credentials
./catalog-build.sh
```

## Features

- **Static Site Generation**: Generates pure HTML/CSS that can be hosted anywhere (S3, CloudFront, Nginx, GitHub Pages)
- **Multi-Tenant Design**: Configure for any eBay seller via YAML config files
- **Auto-Categorization**: Automatically organizes items by eBay category
- **Mobile-First Design**: Responsive layout optimized for mobile shoppers
- **Smart Caching**: Minimizes API calls with configurable response caching
- **eBay Affiliate Support**: Built-in support for eBay Partner Network tracking
- **SEO-Friendly**: Generates sitemap.xml and uses semantic HTML
- **Zero JavaScript Frameworks**: Lightweight, fast-loading pages

## Demo

The generated site includes:
- **Landing Page**: Hero section, category cards, recently listed items
- **Category Pages**: Filtered item grids with pagination
- **Item Cards**: Product images, pricing, condition badges, shipping info
- **Direct eBay Links**: Click-through to purchase on eBay

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- eBay Developer account (free)
- Active eBay seller account

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/jbrahy/ebay-catalog.git
cd ebay-catalog

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

**Note**: All commands below assume you've activated the virtual environment. If not activated, use `venv/bin/python3` instead of `python`.

### 3. Get eBay API Credentials

1. Go to [eBay Developer Program](https://developer.ebay.com/)
2. Sign in or create an account
3. Navigate to **"My Account"** → **"Application Keys"**
4. Create a new application (if you don't have one):
   - Choose **"Get started with your Sandbox keys"**
   - Fill in application details
   - Submit for approval
5. Once approved, you'll see:
   - **App ID (Client ID)** - Copy this
   - **Cert ID (Client Secret)** - Copy this
6. For production use:
   - Click **"Request a Production Key"**
   - Fill out the required information
   - Once approved, copy your Production App ID and Cert ID

### 4. Configure Your Catalog

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit configuration
nano config/config.yaml  # or use your preferred editor
```

**Required Settings**:
```yaml
ebay:
  app_id: "YOUR_APP_ID_HERE"        # From step 3
  cert_id: "YOUR_CERT_ID_HERE"      # From step 3
  environment: "PRODUCTION"          # or "SANDBOX" for testing
  marketplace: "EBAY_US"             # Your marketplace

seller:
  username: "your_ebay_username"    # Your eBay seller username
  display_name: "Your Store Name"   # Displayed on site
  tagline: "Your tagline here"      # Subtitle
```

See `config/config.example.yaml` for all available options.

### 5. Build Your Catalog

```bash
# Generate the catalog site
python build.py

# Or if venv not activated:
venv/bin/python3 build.py

# The static site will be generated in the 'output/' directory
```

### 6. Validate Setup (Optional)

Before building, you can validate your setup:

```bash
venv/bin/python3 validate-setup.py
```

This checks:
- Python version compatibility
- Required modules are installed
- Project structure is complete
- Configuration file exists and is valid

### 7. View Locally

Open `output/index.html` in your web browser to preview your catalog.

## Usage

### Basic Commands

```bash
# Demo mode - generate sample catalog (no eBay API needed)
./catalog-build.sh --demo

# Build with default config (using convenience script)
./catalog-build.sh

# Or activate venv and use python directly
source venv/bin/activate
python build.py

# Use custom config file
./catalog-build.sh --config config/sellers/myshop.yaml

# Force refresh from API (ignore cache)
./catalog-build.sh --force-refresh

# Dry run (fetch data but don't generate site)
./catalog-build.sh --dry-run

# Skip deployment step
./catalog-build.sh --no-deploy

# Enable verbose logging
./catalog-build.sh --verbose
```

**Tip**: The `catalog-build.sh` script automatically uses the virtual environment, so you don't need to activate it first.

### Demo Mode

Waiting for eBay developer approval? Use **demo mode** to generate a fully-functional sample catalog:

```bash
./catalog-build.sh --demo
```

This creates a complete catalog with 40 sample items across 4 categories:
- ✅ No eBay API credentials required
- ✅ Perfect for testing deployment pipelines
- ✅ See what your catalog will look like
- ✅ Test customization and styling changes

The generated demo site is production-ready HTML that you can deploy anywhere to preview the layout and design.

### Configuration Options

See `config/config.example.yaml` for detailed documentation of all configuration options.

**Key Configuration Sections**:

- **ebay**: API credentials and marketplace settings
- **seller**: Seller username, branding, contact info
- **site**: Site title, URL, display options, affiliate settings
- **categories**: Custom category ordering and hiding categories
- **build**: Output paths, cache settings, sitemap generation
- **deploy**: S3 or rsync deployment configuration

### Automated Refreshes with Cron

To keep your catalog up-to-date, set up a cron job:

```bash
# Edit crontab
crontab -e

# Add line to refresh every 15 minutes
*/15 * * * * cd /path/to/ebay-catalog && ./catalog-build.sh >> /var/log/ebay-catalog.log 2>&1

# Or refresh every hour
0 * * * * cd /path/to/ebay-catalog && ./catalog-build.sh >> /var/log/ebay-catalog.log 2>&1

# Or using venv python directly
*/15 * * * * cd /path/to/ebay-catalog && venv/bin/python3 build.py >> /var/log/ebay-catalog.log 2>&1
```

## Deployment Options

### Option 1: AWS S3 + CloudFront

**Best for**: Scalable, CDN-backed hosting with HTTPS

```bash
# Install AWS CLI
pip install awscli

# Configure AWS credentials
aws configure

# Create S3 bucket
aws s3 mb s3://your-catalog-bucket

# Enable static website hosting
aws s3 website s3://your-catalog-bucket --index-document index.html

# Upload site
aws s3 sync output/ s3://your-catalog-bucket --delete

# Optional: Set up CloudFront distribution for CDN + HTTPS
```

Update `config.yaml`:
```yaml
deploy:
  method: "s3"
  s3_bucket: "your-catalog-bucket"
  s3_region: "us-east-1"
```

Then run: `python build.py` (deployment happens automatically)

### Option 2: Traditional Web Server (Nginx, Apache)

**Best for**: Existing hosting, VPS, dedicated server

```bash
# Copy output to web server via rsync
rsync -avz --delete output/ user@yourserver.com:/var/www/catalog/

# Or via SCP
scp -r output/* user@yourserver.com:/var/www/catalog/
```

Update `config.yaml`:
```yaml
deploy:
  method: "rsync"
  rsync_target: "user@yourserver.com:/var/www/catalog"
```

### Option 3: GitHub Pages

**Best for**: Free hosting with custom domain support

```bash
# Create a new branch for GitHub Pages
git checkout --orphan gh-pages

# Copy output to root
cp -r output/* .

# Commit and push
git add .
git commit -m "Deploy catalog"
git push origin gh-pages

# Enable GitHub Pages in repository settings
# Your site will be at: https://yourusername.github.io/ebay-catalog
```

### Option 4: Netlify / Vercel

**Best for**: Simple drag-and-drop deployment

1. Build the site: `python build.py`
2. Drag the `output/` folder to Netlify or Vercel
3. Configure custom domain (optional)

## Project Structure

```
ebay-catalog/
├── build.py                       # Main build script
├── requirements.txt               # Python dependencies
├── config/
│   ├── config.example.yaml        # Configuration template
│   └── sellers/                   # Multi-seller configs (optional)
├── src/
│   ├── ebay_client.py             # eBay API OAuth + Browse API
│   ├── catalog_builder.py         # Category organization logic
│   └── site_generator.py          # Jinja2 template rendering
├── templates/
│   ├── base.html                  # Base layout
│   ├── index.html                 # Homepage template
│   ├── category.html              # Category page template
│   └── item_card.html             # Item card component
├── static/
│   ├── css/styles.css             # Responsive CSS (no frameworks)
│   └── images/                    # Logo, favicon, etc.
├── output/                        # Generated site (gitignored)
└── .cache/                        # API response cache (gitignored)
```

## eBay Affiliate Integration

Earn commission on sales through your catalog:

1. Sign up for [eBay Partner Network](https://partnernetwork.ebay.com/)
2. Get your Campaign ID
3. Add to `config.yaml`:
   ```yaml
   site:
     affiliate_campaign_id: "YOUR_CAMPAIGN_ID"
   ```
4. Rebuild site: `python build.py --force-refresh`

All "View on eBay" links will now include affiliate tracking.

## API Rate Limits

eBay Browse API limits (Individual tier):
- **5,000 calls per day**
- Each pagination request counts as one call
- 200 items max per request

**Cache Strategy**:
- API responses are cached for 15 minutes by default (configurable)
- Cron jobs running every 15 minutes will use mostly cached data
- Use `--force-refresh` only when needed

**Monitoring Usage**:
```bash
# View API calls made during build
python build.py --verbose
```

## Multi-Seller Support

Host catalogs for multiple sellers from one installation:

```bash
# Create seller-specific configs
config/sellers/shop1.yaml
config/sellers/shop2.yaml

# Build each catalog
python build.py --config config/sellers/shop1.yaml
python build.py --config config/sellers/shop2.yaml
```

Each config can specify its own `output_dir` to keep catalogs separate.

## Customization

### Styling

Edit `static/css/styles.css` to customize:
- Colors (CSS variables at top of file)
- Fonts
- Layout spacing
- Card designs

### Templates

Edit templates in `templates/` to modify:
- Page structure
- HTML markup
- Content organization

All templates use Jinja2 syntax.

### Categories

Control category display in `config.yaml`:

```yaml
categories:
  # Show these categories first, in this order
  custom_order:
    - "Electronics"
    - "Collectibles"

  # Hide these categories completely
  hidden:
    - "Adult Only"
```

## Troubleshooting

### "Authentication failed" error

- Verify App ID and Cert ID are correct
- Check environment setting (PRODUCTION vs SANDBOX)
- Ensure credentials haven't expired

### "No items found" error

- Verify seller username is correct
- Check that seller has active listings
- Ensure marketplace setting matches seller's marketplace

### "API rate limit exceeded" error

- Wait until daily limit resets (midnight Pacific Time)
- Increase `cache_ttl_minutes` in config
- Use `--force-refresh` less frequently

### Site looks broken

- Ensure `static/` directory copied to output
- Check browser console for errors
- Verify all template files exist

## Requirements

- Python 3.8+
- httpx >= 0.27.0
- pyyaml >= 6.0.1
- jinja2 >= 3.1.3
- boto3 >= 1.34.34 (optional, for S3 deployment)

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [your-repo-url]/issues
- Documentation: See `docs/ebay-catalog-builder-prompt.md` for detailed specifications

## Credits

Built with:
- [eBay Browse API](https://developer.ebay.com/api-docs/buy/browse/overview.html)
- [Jinja2](https://jinja.palletsprojects.com/)
- [httpx](https://www.python-httpx.org/)
