"""
Static site generator using Jinja2 templates.
Renders HTML pages atomically to prevent broken output.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from xml.etree import ElementTree as ET

from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)


class SiteGenerator:
    """
    Generates static HTML site from catalog data using Jinja2 templates.

    Handles:
    - Rendering index and category pages
    - Pagination for large categories
    - Sitemap generation
    - Atomic output (temp dir then swap)
    - Copying static assets
    """

    def __init__(
        self,
        template_dir: Path,
        static_dir: Path,
        output_dir: Path,
        site_config: Dict[str, Any]
    ):
        """
        Initialize site generator.

        Args:
            template_dir: Path to Jinja2 templates
            static_dir: Path to static assets (css, images)
            output_dir: Path where final site will be written
            site_config: Site configuration dict from config.yaml
        """
        self.template_dir = Path(template_dir)
        self.static_dir = Path(static_dir)
        self.output_dir = Path(output_dir)
        self.site_config = site_config

        # Set up Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )

        # Add custom filters
        self.jinja_env.filters['format'] = lambda value, fmt: fmt % value

    def generate_site(self, catalog: Dict[str, Any]) -> None:
        """
        Generate complete static site from catalog data.

        Uses atomic output: renders to temp dir, then swaps on success.

        Args:
            catalog: Catalog dict from CatalogBuilder

        Raises:
            Exception: If rendering fails
        """
        logger.info("Starting site generation")

        # Create temp output directory
        temp_dir = self.output_dir.parent / f"{self.output_dir.name}.tmp"

        try:
            # Clean temp dir if it exists
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Render all pages to temp directory
            self._render_index(catalog, temp_dir)
            self._render_category_pages(catalog, temp_dir)

            # Generate sitemap if enabled
            if self.site_config.get("generate_sitemap", True):
                self._generate_sitemap(catalog, temp_dir)

            # Copy static assets
            self._copy_static_assets(temp_dir)

            # Atomic swap: remove old output and rename temp
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            temp_dir.rename(self.output_dir)

            logger.info(f"Site generated successfully at {self.output_dir}")

        except Exception as e:
            logger.error(f"Site generation failed: {e}")
            # Clean up temp dir on failure
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise

    def _get_template_context(self, catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build common template context shared across all pages.

        Args:
            catalog: Catalog dict

        Returns:
            Context dict for templates
        """
        # Format generated timestamp
        generated_dt = datetime.fromisoformat(
            catalog["generated_at"].replace("Z", "+00:00")
        )
        generated_formatted = generated_dt.strftime("%B %d, %Y at %I:%M %p UTC")

        return {
            "site": self.site_config,
            "seller": catalog["seller"],
            "categories": catalog["categories"],
            "total_items": catalog["total_items"],
            "generated_at_formatted": generated_formatted,
            "show_price": self.site_config.get("show_price", True),
            "show_shipping": self.site_config.get("show_shipping", True),
            "show_condition": self.site_config.get("show_condition", True),
            "show_time_remaining": self.site_config.get("show_time_remaining", True),
            "base_path": "",  # Root level
        }

    def _render_index(self, catalog: Dict[str, Any], output_dir: Path) -> None:
        """
        Render index.html landing page.

        Args:
            catalog: Catalog dict
            output_dir: Output directory path
        """
        logger.info("Rendering index.html")

        template = self.jinja_env.get_template("index.html")
        context = self._get_template_context(catalog)

        # Add recent items (newest 8 across all categories)
        all_items = []
        for category in catalog["categories"]:
            all_items.extend(category["items"])

        # Sort by title as proxy for newest (could improve with actual listing date)
        recent_items = sorted(all_items, key=lambda x: x["title"])[:8]
        context["recent_items"] = recent_items
        context["current_page"] = "home"

        html = template.render(**context)

        output_file = output_dir / "index.html"
        output_file.write_text(html)

        logger.debug(f"Rendered {output_file}")

    def _render_category_pages(
        self,
        catalog: Dict[str, Any],
        output_dir: Path
    ) -> None:
        """
        Render category pages with pagination.

        Args:
            catalog: Catalog dict
            output_dir: Output directory path
        """
        category_dir = output_dir / "category"
        category_dir.mkdir(exist_ok=True)

        template = self.jinja_env.get_template("category.html")
        items_per_page = self.site_config.get("items_per_page", 24)

        for category in catalog["categories"]:
            logger.info(f"Rendering category: {category['name']}")

            items = category["items"]
            total_items = len(items)
            total_pages = (total_items + items_per_page - 1) // items_per_page

            # Render each page
            for page_num in range(1, total_pages + 1):
                start_idx = (page_num - 1) * items_per_page
                end_idx = start_idx + items_per_page
                page_items = items[start_idx:end_idx]

                context = self._get_template_context(catalog)
                context.update({
                    "category": category,
                    "items": page_items,
                    "current_category": category["slug"],
                    "page": page_num,
                    "total_pages": total_pages,
                    "has_pagination": total_pages > 1,
                    "base_path": "../",
                })

                html = template.render(**context)

                # File naming: first page is category-slug.html, others are category-slug-pageN.html
                if page_num == 1:
                    output_file = category_dir / f"{category['slug']}.html"
                else:
                    output_file = category_dir / f"{category['slug']}-page{page_num}.html"

                output_file.write_text(html)
                logger.debug(f"Rendered {output_file}")

    def _generate_sitemap(self, catalog: Dict[str, Any], output_dir: Path) -> None:
        """
        Generate sitemap.xml for SEO.

        Args:
            catalog: Catalog dict
            output_dir: Output directory path
        """
        logger.info("Generating sitemap.xml")

        base_url = self.site_config.get("base_url", "").rstrip("/")
        if not base_url:
            logger.warning("base_url not set in config, skipping sitemap")
            return

        # Create XML structure
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        # Add index page
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = f"{base_url}/index.html"
        ET.SubElement(url, "changefreq").text = "daily"
        ET.SubElement(url, "priority").text = "1.0"

        # Add category pages
        for category in catalog["categories"]:
            url = ET.SubElement(urlset, "url")
            ET.SubElement(url, "loc").text = f"{base_url}/category/{category['slug']}.html"
            ET.SubElement(url, "changefreq").text = "daily"
            ET.SubElement(url, "priority").text = "0.8"

        # Write sitemap
        tree = ET.ElementTree(urlset)
        ET.indent(tree, space="  ")
        sitemap_file = output_dir / "sitemap.xml"
        tree.write(sitemap_file, encoding="utf-8", xml_declaration=True)

        logger.debug(f"Rendered {sitemap_file}")

    def _copy_static_assets(self, output_dir: Path) -> None:
        """
        Copy static assets (CSS, images) to output directory.

        Args:
            output_dir: Output directory path
        """
        logger.info("Copying static assets")

        output_static = output_dir / "static"

        if self.static_dir.exists():
            shutil.copytree(
                self.static_dir,
                output_static,
                dirs_exist_ok=True
            )
            logger.debug(f"Copied {self.static_dir} to {output_static}")
        else:
            logger.warning(f"Static directory not found: {self.static_dir}")
