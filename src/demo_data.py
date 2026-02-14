"""
Demo data generator for testing the catalog without eBay API access.
Generates realistic-looking sample items across multiple categories.
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Any


# Sample product data
ELECTRONICS = [
    "Sony WH-1000XM4 Wireless Headphones",
    "Apple AirPods Pro 2nd Generation",
    "Samsung Galaxy Tab S8 Tablet",
    "Logitech MX Master 3S Mouse",
    "Blue Yeti USB Microphone",
    "Canon EOS Rebel T7 DSLR Camera",
    "Anker PowerCore 20100mAh Power Bank",
    "Kindle Paperwhite E-Reader",
    "Ring Video Doorbell Pro",
    "Bose SoundLink Mini Bluetooth Speaker",
]

COLLECTIBLES = [
    "Vintage Star Wars Action Figures Set",
    "Pokemon Card Collection Lot",
    "Marvel Legends Iron Man Figure",
    "Funko Pop! Marvel Avengers Set",
    "Rare Vinyl Record The Beatles Abbey Road",
    "Limited Edition Hot Wheels Collection",
    "Vintage Coca-Cola Tin Sign",
    "Sports Trading Cards Bundle",
    "Disney VHS Tapes Collection",
    "Comic Book Lot Spider-Man Issues",
]

HOME_GARDEN = [
    "Instant Pot Duo 7-in-1 Pressure Cooker",
    "Dyson V11 Cordless Vacuum",
    "Ninja Air Fryer 6 Quart",
    "Keurig K-Elite Coffee Maker",
    "Indoor Plant Collection with Pots",
    "Garden Tool Set 10 Pieces",
    "LED String Lights Outdoor 50ft",
    "Memory Foam Pillow Set of 2",
    "Throw Blanket Soft Fleece",
    "Wall Art Canvas Prints Set",
]

TOYS_HOBBIES = [
    "LEGO Star Wars Millennium Falcon",
    "Barbie Dreamhouse Playset",
    "Hot Wheels Track Set Mega Loop",
    "Nerf N-Strike Elite Blaster",
    "RC Car Off-Road Monster Truck",
    "Puzzle 1000 Pieces Landscape",
    "Board Game Collection Bundle",
    "Art Supply Set Drawing Kit",
    "Rubik's Cube Speed Cube",
    "Model Train Set Complete",
]

CATEGORIES = {
    "Electronics": ELECTRONICS,
    "Collectibles": COLLECTIBLES,
    "Home & Garden": HOME_GARDEN,
    "Toys & Hobbies": TOYS_HOBBIES,
}

CONDITIONS = ["New", "Like New", "Used - Excellent", "Used - Good"]

SAMPLE_IMAGES = [
    "https://i.ebayimg.com/images/g/placeholder1.jpg",
    "https://i.ebayimg.com/images/g/placeholder2.jpg",
    "https://i.ebayimg.com/images/g/placeholder3.jpg",
]


def generate_item_id() -> str:
    """Generate fake eBay item ID."""
    return f"v1|{random.randint(100000000000, 999999999999)}|0"


def generate_demo_items(count: int = 40) -> List[Dict[str, Any]]:
    """
    Generate demo items with realistic data.

    Args:
        count: Number of items to generate

    Returns:
        List of normalized item dicts matching eBay client format
    """
    items = []

    # Distribute items across categories
    for category_name, products in CATEGORIES.items():
        items_in_category = min(count // len(CATEGORIES), len(products))

        for i in range(items_in_category):
            title = products[i % len(products)]

            # Random price between $10 and $500
            price_value = round(random.uniform(10, 500), 2)

            # 20% chance of being an auction
            is_auction = random.random() < 0.2

            # Random condition
            condition = random.choice(CONDITIONS)

            # Shipping
            if random.random() < 0.4:  # 40% free shipping
                shipping_cost = {"value": 0.0, "currency": "USD"}
                shipping_type = "FREE"
            else:
                shipping_cost = {
                    "value": round(random.uniform(4.99, 19.99), 2),
                    "currency": "USD"
                }
                shipping_type = "CALCULATED"

            # Current bid for auctions
            current_bid = None
            if is_auction:
                current_bid = {
                    "value": round(price_value * random.uniform(0.5, 0.9), 2),
                    "currency": "USD"
                }

            # Auction end date (1-7 days from now)
            item_end_date = ""
            if is_auction:
                end_dt = datetime.utcnow() + timedelta(days=random.randint(1, 7))
                item_end_date = end_dt.isoformat() + "Z"

            # Buying options
            buying_options = []
            if is_auction:
                buying_options.append("AUCTION")
            else:
                buying_options.append("FIXED_PRICE")
                if random.random() < 0.3:  # 30% have best offer
                    buying_options.append("BEST_OFFER")

            item = {
                "item_id": generate_item_id(),
                "title": title,
                "price": {
                    "value": price_value,
                    "currency": "USD"
                },
                "current_bid": current_bid,
                "primary_image": random.choice(SAMPLE_IMAGES),
                "additional_images": random.sample(SAMPLE_IMAGES, k=random.randint(0, 2)),
                "condition": condition,
                "category": category_name,
                "item_url": f"https://www.ebay.com/itm/{generate_item_id()}",
                "shipping_cost": shipping_cost,
                "shipping_type": shipping_type,
                "location": random.choice(["Los Angeles, CA", "New York, NY", "Chicago, IL", "Miami, FL"]),
                "buying_options": buying_options,
                "item_end_date": item_end_date,
                "is_auction": is_auction,
                "is_buy_it_now": "FIXED_PRICE" in buying_options,
                "is_best_offer": "BEST_OFFER" in buying_options,
            }

            items.append(item)

    return items


def get_demo_seller_info() -> Dict[str, Any]:
    """Get demo seller information."""
    return {
        "username": "demo_seller",
        "display_name": "Demo's Deals & Finds",
        "tagline": "Quality products at great prices - Demo Mode",
        "logo": "",
        "contact_email": "demo@example.com"
    }
