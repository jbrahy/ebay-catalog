"""
Deployment module for pushing generated site to S3 or remote server.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Deployer:
    """
    Handles deployment of generated static site.

    Supports:
    - AWS S3 (with optional CloudFront invalidation)
    - rsync to remote server
    """

    def __init__(self, deploy_config: Dict[str, Any], output_dir: Path):
        """
        Initialize deployer.

        Args:
            deploy_config: Deploy section from config.yaml
            output_dir: Path to generated site output
        """
        self.config = deploy_config
        self.output_dir = Path(output_dir)
        self.method = deploy_config.get("method", "none")

    def deploy(self) -> bool:
        """
        Deploy site based on configured method.

        Returns:
            True if deployment succeeded, False otherwise
        """
        if self.method == "none":
            logger.info("Deployment method is 'none', skipping deployment")
            return True

        if not self.output_dir.exists():
            logger.error(f"Output directory does not exist: {self.output_dir}")
            return False

        logger.info(f"Starting deployment via {self.method}")

        try:
            if self.method == "s3":
                return self._deploy_s3()
            elif self.method == "rsync":
                return self._deploy_rsync()
            else:
                logger.error(f"Unknown deployment method: {self.method}")
                return False

        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            return False

    def _deploy_s3(self) -> bool:
        """
        Deploy to AWS S3 using AWS CLI.

        Returns:
            True if successful
        """
        bucket = self.config.get("s3_bucket")
        region = self.config.get("s3_region", "us-east-1")

        if not bucket:
            logger.error("s3_bucket not configured")
            return False

        logger.info(f"Deploying to S3 bucket: {bucket}")

        # Build aws s3 sync command
        cmd = [
            "aws", "s3", "sync",
            str(self.output_dir),
            f"s3://{bucket}",
            "--delete",  # Remove files not in source
            "--region", region
        ]

        # Add cache control headers for common file types
        cache_rules = [
            ("--exclude", "*"),
            ("--include", "*.html"),
            ("--cache-control", "max-age=300, public"),  # 5 min for HTML
            ("--exclude", "*"),
            ("--include", "*.css"),
            ("--cache-control", "max-age=31536000, public"),  # 1 year for CSS
            ("--exclude", "*"),
            ("--include", "*.js"),
            ("--cache-control", "max-age=31536000, public"),  # 1 year for JS
            ("--exclude", "*"),
            ("--include", "*.jpg"),
            ("--include", "*.jpeg"),
            ("--include", "*.png"),
            ("--include", "*.gif"),
            ("--include", "*.webp"),
            ("--cache-control", "max-age=31536000, public"),  # 1 year for images
        ]

        try:
            # Run sync command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("S3 sync completed successfully")
            logger.debug(result.stdout)

            # CloudFront invalidation (if distribution ID provided)
            distribution_id = self.config.get("cloudfront_distribution_id")
            if distribution_id:
                self._invalidate_cloudfront(distribution_id)

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"S3 sync failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error(
                "AWS CLI not found. Install with: pip install awscli && aws configure"
            )
            return False

    def _invalidate_cloudfront(self, distribution_id: str) -> bool:
        """
        Create CloudFront invalidation to clear CDN cache.

        Args:
            distribution_id: CloudFront distribution ID

        Returns:
            True if successful
        """
        logger.info(f"Creating CloudFront invalidation for {distribution_id}")

        cmd = [
            "aws", "cloudfront", "create-invalidation",
            "--distribution-id", distribution_id,
            "--paths", "/*"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("CloudFront invalidation created")
            logger.debug(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            logger.warning(f"CloudFront invalidation failed: {e.stderr}")
            return False

    def _deploy_rsync(self) -> bool:
        """
        Deploy to remote server using rsync.

        Returns:
            True if successful
        """
        target = self.config.get("rsync_target")

        if not target:
            logger.error("rsync_target not configured")
            return False

        logger.info(f"Deploying to remote server: {target}")

        # Build rsync command
        # -a = archive mode (recursive, preserve permissions, times, etc.)
        # -v = verbose
        # -z = compress during transfer
        # --delete = remove files not in source
        cmd = [
            "rsync",
            "-avz",
            "--delete",
            str(self.output_dir) + "/",  # Trailing slash = sync contents
            target
        ]

        # Add optional rsync flags if configured
        extra_flags = self.config.get("rsync_flags", [])
        if extra_flags:
            cmd[1:1] = extra_flags  # Insert after 'rsync'

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info("rsync completed successfully")
            logger.debug(result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"rsync failed: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("rsync not found. Install rsync on your system.")
            return False


def deploy_site(deploy_config: Dict[str, Any], output_dir: Path) -> bool:
    """
    Convenience function to deploy a site.

    Args:
        deploy_config: Deploy configuration dict
        output_dir: Path to generated site

    Returns:
        True if deployment succeeded
    """
    deployer = Deployer(deploy_config, output_dir)
    return deployer.deploy()
