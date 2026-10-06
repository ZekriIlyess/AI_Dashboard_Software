"""
Nexus AI — Seed Test Database
==============================
Seeds the test PostgreSQL database (port 5433) with sample e-commerce data
for development and testing. This simulates a customer's database.

Usage:
    python scripts/seed-test-db.py

The test database runs on port 5433 (separate from the app DB on 5432).
"""

import asyncio
import random
from datetime import datetime, timedelta

import asyncpg


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TEST_DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "user": "testuser",
    "password": "testpassword",
    "database": "sample_ecommerce",
}

# ---------------------------------------------------------------------------
# Schema Definition
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
-- Drop existing tables (for re-seeding)
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Categories
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    price DECIMAL(10, 2) NOT NULL,
    cost DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customers
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'US',
    signup_date DATE NOT NULL,
    is_churned BOOLEAN DEFAULT FALSE,
    lifetime_value DECIMAL(12, 2) DEFAULT 0,
    support_tickets INTEGER DEFAULT 0,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'completed',
    channel VARCHAR(50) DEFAULT 'web',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order Items
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(12, 2) NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_customers_signup_date ON customers(signup_date);
CREATE INDEX idx_customers_is_churned ON customers(is_churned);
"""

# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("Electronics", "Phones, laptops, tablets, and accessories"),
    ("Clothing", "Men's and women's apparel"),
    ("Home & Kitchen", "Furniture, cookware, and home decor"),
    ("Sports & Outdoors", "Fitness equipment, camping, and sports gear"),
    ("Books & Media", "Books, e-books, and digital media"),
    ("Health & Beauty", "Skincare, supplements, and personal care"),
]

PRODUCT_NAMES = {
    "Electronics": ["Wireless Earbuds", "USB-C Charger", "Laptop Stand", "Mechanical Keyboard", "4K Monitor", "Webcam HD", "Portable SSD", "Smart Watch"],
    "Clothing": ["Classic T-Shirt", "Slim Jeans", "Running Shoes", "Winter Jacket", "Cotton Hoodie", "Dress Shirt", "Yoga Pants", "Baseball Cap"],
    "Home & Kitchen": ["Coffee Maker", "Air Fryer", "Throw Pillow Set", "LED Desk Lamp", "Cutting Board Set", "Storage Containers", "Bath Towel Set", "Wall Clock"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Running Belt", "Water Bottle", "Camping Tent", "Hiking Backpack", "Resistance Bands", "Jump Rope"],
    "Books & Media": ["Python Cookbook", "Data Science Guide", "Sci-Fi Novel", "Business Strategy", "Meditation Guide", "Cooking Basics", "Art History", "Travel Journal"],
    "Health & Beauty": ["Vitamin D3", "Face Moisturizer", "Protein Powder", "Essential Oils Set", "Sunscreen SPF50", "Hair Serum", "Hand Cream", "Sleep Supplement"],
}

CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "San Francisco", "Seattle", "Austin", "Denver", "Miami",
          "London", "Paris", "Berlin", "Toronto", "Sydney", "Tokyo", "Singapore", "Dubai", "Mumbai", "São Paulo"]

CHANNELS = ["web", "mobile", "email", "social", "referral"]
STATUSES = ["completed", "completed", "completed", "completed", "shipped", "processing", "returned", "cancelled"]

FIRST_NAMES = ["Emma", "Liam", "Olivia", "Noah", "Ava", "James", "Sophia", "Lucas", "Mia", "Mason",
               "Isabella", "Ethan", "Charlotte", "Aiden", "Amelia", "Logan", "Harper", "Alexander", "Evelyn", "Sebastian"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Anderson", "Taylor", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Moore", "Allen"]


async def seed_database():
    """Main seeding function."""
    print("🔌 Connecting to test database...")
    conn = await asyncpg.connect(**TEST_DB_CONFIG)

    try:
        # Create schema
        print("📋 Creating schema...")
        await conn.execute(SCHEMA_SQL)

        # Seed categories
        print("📁 Seeding categories...")
        for name, desc in CATEGORIES:
            await conn.execute(
                "INSERT INTO categories (name, description) VALUES ($1, $2)",
                name, desc,
            )

        # Seed products
        print("📦 Seeding products...")
        product_id = 0
        for cat_idx, (cat_name, _) in enumerate(CATEGORIES, 1):
            for prod_name in PRODUCT_NAMES[cat_name]:
                price = round(random.uniform(9.99, 299.99), 2)
                cost = round(price * random.uniform(0.3, 0.7), 2)
                stock = random.randint(0, 500)
                await conn.execute(
                    "INSERT INTO products (name, category_id, price, cost, stock_quantity) VALUES ($1, $2, $3, $4, $5)",
                    prod_name, cat_idx, price, cost, stock,
                )
                product_id += 1

        # Seed customers
        print("👥 Seeding customers (1,000)...")
        num_customers = 1000
        base_date = datetime(2023, 1, 1)
        for i in range(num_customers):
            signup = base_date + timedelta(days=random.randint(0, 900))
            is_churned = random.random() < 0.15  # 15% churn rate
            support_tickets = random.choices([0, 1, 2, 3, 4, 5, 8, 12], weights=[40, 25, 15, 8, 5, 4, 2, 1])[0]
            last_login = signup + timedelta(days=random.randint(0, 365)) if not is_churned else signup + timedelta(days=random.randint(30, 180))

            await conn.execute(
                """INSERT INTO customers (email, first_name, last_name, city, country, signup_date, is_churned, support_tickets, last_login)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
                f"user{i}@example.com",
                random.choice(FIRST_NAMES),
                random.choice(LAST_NAMES),
                random.choice(CITIES),
                random.choice(["US", "US", "US", "UK", "CA", "DE", "FR", "AU", "JP", "BR"]),
                signup.date(),
                is_churned,
                support_tickets,
                last_login,
            )

        # Seed orders
        print("🛒 Seeding orders (5,000)...")
        num_orders = 5000
        product_count = sum(len(v) for v in PRODUCT_NAMES.values())

        for i in range(num_orders):
            customer_id = random.randint(1, num_customers)
            order_date = base_date + timedelta(days=random.randint(0, 900), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            num_items = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
            status = random.choice(STATUSES)
            channel = random.choice(CHANNELS)

            # Calculate order total from items
            total = 0
            items = []
            for _ in range(num_items):
                prod_id = random.randint(1, product_count)
                qty = random.randint(1, 3)
                # Get a random price (we don't query the DB for speed)
                unit_price = round(random.uniform(9.99, 299.99), 2)
                item_total = round(unit_price * qty, 2)
                total += item_total
                items.append((prod_id, qty, unit_price, item_total))

            discount = round(total * random.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20]), 2)
            total_after_discount = round(total - discount, 2)

            order_id = await conn.fetchval(
                """INSERT INTO orders (customer_id, order_date, total_amount, discount_amount, status, channel)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                customer_id, order_date, total_after_discount, discount, status, channel,
            )

            # Insert order items
            for prod_id, qty, unit_price, item_total in items:
                await conn.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, total_price) VALUES ($1, $2, $3, $4, $5)",
                    order_id, prod_id, qty, unit_price, item_total,
                )

        # Update customer lifetime values
        print("💰 Calculating lifetime values...")
        await conn.execute("""
            UPDATE customers c
            SET lifetime_value = COALESCE(
                (SELECT SUM(o.total_amount) FROM orders o WHERE o.customer_id = c.id AND o.status = 'completed'),
                0
            )
        """)

        # Print summary
        counts = await conn.fetch("""
            SELECT 'categories' as tbl, COUNT(*) as cnt FROM categories
            UNION ALL SELECT 'products', COUNT(*) FROM products
            UNION ALL SELECT 'customers', COUNT(*) FROM customers
            UNION ALL SELECT 'orders', COUNT(*) FROM orders
            UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
        """)

        print("\n✅ Database seeded successfully!")
        print("=" * 40)
        for row in counts:
            print(f"  {row['tbl']:>15}: {row['cnt']:,} rows")
        print("=" * 40)
        print(f"\n🔗 Connection: postgresql://testuser:testpassword@localhost:5433/sample_ecommerce")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
