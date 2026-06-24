"""Configuration for Football Predict App"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Flask
SECRET_KEY = os.environ.get('SECRET_KEY', 'fp-secret-key-change-in-production')

# Engine data directory
ENGINE_DATA_DIR = os.path.join(BASE_DIR, 'engine', 'data')

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'database.sqlite')

# Admin
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'fp-admin-2026')  # Change this!

# Card settings
CARD_PREFIX = 'FP'
CARD_SEGMENTS = 4  # 4 segments of 4 chars each

# Pricing: 1场 ¥9.9, 2场+ 打8折
BASE_PRICE = 9.9
DISCOUNT_THRESHOLD = 2   # 2场及以上打折
DISCOUNT_RATE = 0.8      # 8折

def calc_price(matches: int) -> float:
    """Calculate price for n matches"""
    total = matches * BASE_PRICE
    if matches >= DISCOUNT_THRESHOLD:
        total = total * DISCOUNT_RATE
    return round(total, 1)

# Generate tier options for frontend
def get_price_tiers():
    tiers = []
    for n in range(1, 11):
        price = calc_price(n)
        discount_tag = f' (8折)' if n >= DISCOUNT_THRESHOLD else ''
        tiers.append({
            'id': f'm{n}',
            'credits': n,
            'price': price,
            'label': f'{n}场',
            'tag': discount_tag,
        })
    return tiers

# Card-based pricing (backward compat for admin card generation)
PRICE_TIERS = {
    'm1':  {'credits': 1,  'label': '1场 (¥9.9)'},
    'm2':  {'credits': 2,  'label': '2场 (¥15.8, 8折)'},
    'm3':  {'credits': 3,  'label': '3场 (¥23.8, 8折)'},
    'm5':  {'credits': 5,  'label': '5场 (¥39.6, 8折)'},
    'm10': {'credits': 10, 'label': '10场 (¥79.2, 8折)'},
}
