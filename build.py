#!/usr/bin/env python3
"""
eBay Catalog Builder - Main Build Script

Orchestrates the entire static site generation process:
1. Load and validate configuration
2. Authenticate with eBay API
3. Fetch seller's listings
4. Build categorized catalog
5. Render static HTML site
6. Optionally deploy to S3 or rsync
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

# Import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ebay_client import EbayClient
from catalog_builder import CatalogBuilder
from site_generator import SiteGenerator


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def load_config(config_path: Path) -> dict:
    """
    Load and validate configuration file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Config dict

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config is invalid YAML
        KeyError: If required config keys are missing
    """
    logger.info(f"Loading configuration from {config_path}")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Validate required top-level keys
    required_keys = ['ebay', 'seller', 'site', 'build']
    missing = [key for key in required_keys if key not in config]
    if missing:
        raise KeyError(f"Missing required config keys: {missing}")

    # Validate eBay credentials
    required_ebay = ['app_id', 'cert_id', 'marketplace']
    missing_ebay = [key for key in required_ebay if key not in config['ebay']]
    if missing_ebay:
        raise KeyError(f"Missing required eBay config: {missing_ebay}")

    # Validate seller info
    if 'username' not in config['seller']:
        raise KeyError("Missing seller.username in config")

    logger.info("Configuration loaded successfully")
    return config


def build_catalog(args: argparse.Namespace) -> None:
    """
    Main build function - orchestrates entire process.

    Args:
        args: Parsed command-line arguments
    """
    start_time = time.time()

    try:
        # Load configuration
        config_path = Path(args.config)
        config = load_config(config_path)

        # Extract config sections
        ebay_config = config['ebay']
        seller_config = config['seller']
        site_config = config['site']
        build_config = config['build']
        category_config = config.get('categories', {})

        # Set up paths
        project_root = Path(__file__).parent
        cache_dir = project_root / build_config.get('cache_dir', '.cache')
        output_dir = project_root / build_config.get('output_dir', 'output')
        template_dir = project_root / 'templates'
        static_dir = project_root / 'static'

        # Initialize eBay client
        logger.info("Initializing eBay API client")
        client = EbayClient(
            app_id=ebay_config['app_id'],
            cert_id=ebay_config['cert_id'],
            environment=ebay_config.get('environment', 'PRODUCTION'),
            marketplace=ebay_config.get('marketplace', 'EBAY_US'),
            cache_dir=cache_dir,
            cache_ttl_minutes=build_config.get('cache_ttl_minutes', 15),
            affiliate_campaign_id=site_config.get('affiliate_campaign_id')
        )

        # Dry run check
        if args.dry_run:
            logger.info("DRY RUN MODE - will not write output")

        # Fetch all seller items
        logger.info(f"Fetching items for seller: {seller_config['username']}")
        items = client.get_all_seller_items(
            seller_username=seller_config['username'],
            force_refresh=args.force_refresh
        )

        logger.info(f"API calls made: {client.api_calls_made}")

        if not items:
            logger.warning("No items found for seller")
            return

        # Build catalog
        logger.info("Building catalog structure")
        catalog_builder = CatalogBuilder(
            custom_category_order=category_config.get('custom_order', []),
            hidden_categories=category_config.get('hidden', [])
        )

        catalog = catalog_builder.build_catalog(items, seller_config)

        # Generate static site
        if not args.dry_run:
            logger.info("Generating static site")
            generator = SiteGenerator(
                template_dir=template_dir,
                static_dir=static_dir,
                output_dir=output_dir,
                site_config=site_config
            )

            generator.generate_site(catalog)

            # Deploy if configured and not disabled
            if not args.no_deploy and config.get('deploy', {}).get('method') != 'none':
                logger.info("Deployment configured but not yet implemented")
                # TODO: Implement deployment
        else:
            logger.info("Skipping site generation (dry run)")

        # Print summary
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("BUILD SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Seller: {seller_config.get('display_name', seller_config['username'])}")
        logger.info(f"Total items: {catalog['total_items']}")
        logger.info(f"Categories: {len(catalog['categories'])}")
        logger.info(f"API calls made: {client.api_calls_made}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info("=" * 60)

        if not args.dry_run:
            logger.info(f"✓ Site generated successfully at {output_dir}")
            logger.info(f"  Open {output_dir / 'index.html'} in a browser to view")

    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Parse arguments and run build."""
    parser = argparse.ArgumentParser(
        description="eBay Catalog Static Site Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default config
  %(prog)s --config sellers/shop1.yaml       # Use custom config
  %(prog)s --force-refresh                   # Ignore cache, fetch fresh data
  %(prog)s --dry-run                         # Test without writing output
  %(prog)s --no-deploy                       # Skip deployment step
        """
    )

    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--force-refresh',
        action='store_true',
        help='Ignore cache and fetch fresh data from eBay API'
    )

    parser.add_argument(
        '--no-deploy',
        action='store_true',
        help='Skip deployment step even if configured'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fetch and build catalog but do not write output or deploy'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run build
    build_catalog(args)


if __name__ == '__main__':
    main()
