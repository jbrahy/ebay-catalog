#!/usr/bin/env python3
"""
Setup validation script - checks if everything is configured correctly.
"""

import os
import sys
from pathlib import Path

# Auto-detect and use venv if not already running from it
def ensure_venv():
    """Check if running from venv, and re-exec with venv python if available."""
    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return  # Already in venv

    # Check if venv exists in project directory
    script_dir = Path(__file__).parent
    venv_python = script_dir / 'venv' / 'bin' / 'python3'

    if venv_python.exists():
        # Re-execute this script with venv python
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    # If no venv exists, continue with system python (will show errors)

ensure_venv()

def validate_setup():
    """Validate that the environment is set up correctly."""

    print("eBay Catalog Builder - Setup Validation")
    print("=" * 60)

    errors = []
    warnings = []

    # Check Python version
    print("\n1. Checking Python version...")
    if sys.version_info < (3, 8):
        errors.append(f"Python 3.8+ required, found {sys.version}")
    else:
        print(f"   ✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    # Check required modules
    print("\n2. Checking required Python modules...")
    required_modules = ['yaml', 'httpx', 'jinja2']

    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✓ {module}")
        except ImportError:
            errors.append(f"Missing required module: {module}")
            print(f"   ✗ {module} - NOT FOUND")

    # Check project structure
    print("\n3. Checking project structure...")
    required_dirs = ['src', 'templates', 'static', 'config']
    project_root = Path(__file__).parent

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"   ✓ {dir_name}/")
        else:
            errors.append(f"Missing directory: {dir_name}")
            print(f"   ✗ {dir_name}/ - NOT FOUND")

    # Check required files
    print("\n4. Checking required files...")
    required_files = [
        'build.py',
        'requirements.txt',
        'src/ebay_client.py',
        'src/catalog_builder.py',
        'src/site_generator.py',
        'src/deploy.py',
        'templates/base.html',
        'templates/index.html',
        'templates/category.html',
        'static/css/styles.css',
    ]

    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"   ✓ {file_path}")
        else:
            errors.append(f"Missing file: {file_path}")
            print(f"   ✗ {file_path} - NOT FOUND")

    # Check configuration
    print("\n5. Checking configuration...")
    config_path = project_root / 'config' / 'config.yaml'

    if config_path.exists():
        print(f"   ✓ config/config.yaml exists")

        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Check for placeholder values
            if config.get('ebay', {}).get('app_id') == 'YOUR_APP_ID_HERE':
                warnings.append("eBay app_id is still placeholder value")
                print(f"   ⚠ app_id needs to be configured")

            if config.get('ebay', {}).get('cert_id') == 'YOUR_CERT_ID_HERE':
                warnings.append("eBay cert_id is still placeholder value")
                print(f"   ⚠ cert_id needs to be configured")

            if config.get('seller', {}).get('username') == 'your_ebay_username':
                warnings.append("Seller username is still placeholder value")
                print(f"   ⚠ seller username needs to be configured")

        except Exception as e:
            errors.append(f"Error reading config: {e}")
            print(f"   ✗ Error reading config: {e}")
    else:
        warnings.append("config/config.yaml not found (copy from config.example.yaml)")
        print(f"   ⚠ config/config.yaml not found")
        print(f"     Run: cp config/config.example.yaml config/config.yaml")

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    if not errors and not warnings:
        print("✓ All checks passed! Setup is complete.")
        print("\nNext steps:")
        print("  1. Configure config/config.yaml with your eBay API credentials")
        print("  2. Run: ./catalog-build.sh --dry-run")
        return 0

    if warnings:
        print(f"\n⚠ {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print(f"\n✗ {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease fix the errors above before running the catalog builder.")
        return 1

    if warnings and not errors:
        print("\n⚠ Setup is mostly complete, but you need to configure your eBay API credentials.")
        print("\nEdit config/config.yaml and add:")
        print("  - eBay App ID (from https://developer.ebay.com/)")
        print("  - eBay Cert ID (Client Secret)")
        print("  - Seller username")
        return 0

if __name__ == '__main__':
    sys.exit(validate_setup())
