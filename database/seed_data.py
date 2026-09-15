from database.database import get_db_connection, DEFAULT_DB_PATH
from database.init_db import init_database

EXPENSES_SEED = [
    # September 2026 - Food (Total = 6000)
    ("2026-09-02", "Food", 2500.0, "Supermarket Groceries"),
    ("2026-09-12", "Food", 1500.0, "Weekend Restaurant Dinner"),
    ("2026-09-20", "Food", 2000.0, "Organic Food Store"),

    # September 2026 - Transport (Total = 2000)
    ("2026-09-05", "Transport", 1200.0, "Vehicle Fuel Refill"),
    ("2026-09-18", "Transport", 800.0, "Metro Pass & Cab Fares"),

    # September 2026 - Shopping (Total = 5000)
    ("2026-09-08", "Shopping", 3500.0, "Autumn Clothing Purchase"),
    ("2026-09-22", "Shopping", 1500.0, "Home Accessories"),

    # September 2026 - Bills (Total = 5500)
    ("2026-09-10", "Bills", 4000.0, "Electricity & Water Bill"),
    ("2026-09-15", "Bills", 1500.0, "Fiber Broadband & Mobile Plan"),

    # September 2026 - Entertainment (Total = 2000)
    ("2026-09-06", "Entertainment", 1200.0, "Movie Tickets & Snacks"),
    ("2026-09-25", "Entertainment", 800.0, "Music Streaming Subscriptions"),

    # August 2026 - Food (Total = 4800)
    ("2026-08-04", "Food", 2000.0, "Weekly Grocery Run"),
    ("2026-08-14", "Food", 1800.0, "Family Dining Out"),
    ("2026-08-25", "Food", 1000.0, "Cafes & Bakery"),

    # August 2026 - Transport (Total = 1500)
    ("2026-08-08", "Transport", 1500.0, "Monthly Commute Expenses"),

    # August 2026 - Shopping (Total = 2500)
    ("2026-08-18", "Shopping", 2500.0, "Footwear & Apparel"),

    # August 2026 - Bills (Total = 5000)
    ("2026-08-10", "Bills", 5000.0, "Utility Bills"),

    # August 2026 - Entertainment (Total = 1500)
    ("2026-08-22", "Entertainment", 1500.0, "Weekend Outing"),

    # --- 2025 Historical Data ---
    ("2025-01-05", "Bills", 4800.0, "Winter Electricity & Heating"),
    ("2025-01-15", "Food", 3500.0, "New Year Groceries"),
    ("2025-05-10", "Transport", 1600.0, "Commute & Fuel Refill"),
    ("2025-05-18", "Healthcare", 2500.0, "Annual Medical Checkup"),
    ("2025-09-04", "Food", 4000.0, "Monthly Supermarket Groceries"),
    ("2025-09-15", "Shopping", 6500.0, "Home Appliances & Electronics"),
    ("2025-11-20", "Entertainment", 2200.0, "Music Concert & Theater"),

    # --- 2024 Historical Data ---
    ("2024-03-10", "Food", 3000.0, "Groceries & Weekly Dining"),
    ("2024-03-15", "Bills", 4500.0, "Water, Gas & High-Speed Fiber"),
    ("2024-06-20", "Travel", 12000.0, "Summer Vacation Flight & Resort"),
    ("2024-06-25", "Shopping", 4000.0, "Summer Wardrobe Clearance"),
    ("2024-11-12", "Transport", 1800.0, "Annual Vehicle Maintenance"),
    ("2024-12-24", "Entertainment", 3500.0, "Holiday Season Gifts & Outing"),
    ("2024-12-28", "Food", 4200.0, "Year-End Celebration Feast"),
]

BUDGETS_SEED = [
    # September 2026 Budgets
    ("Food", "2026-09", 5000.0),
    ("Transport", "2026-09", 3000.0),
    ("Shopping", "2026-09", 6000.0),
    ("Bills", "2026-09", 6000.0),
    ("Entertainment", "2026-09", 1500.0),

    # August 2026 Budgets
    ("Food", "2026-08", 5000.0),
    ("Transport", "2026-08", 2500.0),
    ("Shopping", "2026-08", 4000.0),
    ("Bills", "2026-08", 5500.0),
    ("Entertainment", "2026-08", 2000.0),

    # --- 2025 Budgets ---
    ("Bills", "2025-01", 5000.0),
    ("Food", "2025-01", 4000.0),
    ("Transport", "2025-05", 2000.0),
    ("Healthcare", "2025-05", 3000.0),
    ("Food", "2025-09", 4500.0),
    ("Shopping", "2025-09", 5000.0),
    ("Entertainment", "2025-11", 2500.0),

    # --- 2024 Budgets ---
    ("Food", "2024-03", 4000.0),
    ("Bills", "2024-03", 5000.0),
    ("Travel", "2024-06", 15000.0),
    ("Shopping", "2024-06", 5000.0),
    ("Transport", "2024-11", 2000.0),
    ("Entertainment", "2024-12", 3000.0),
    ("Food", "2024-12", 4500.0),
]

def seed_database(db_path: str = DEFAULT_DB_PATH) -> None:
    """Clear existing tables and seed sample records."""
    init_database(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM expenses")
    cursor.execute("DELETE FROM budgets")

    cursor.executemany(
        "INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)",
        EXPENSES_SEED
    )

    cursor.executemany(
        "INSERT INTO budgets (category, month, budget_amount) VALUES (?, ?, ?)",
        BUDGETS_SEED
    )

    conn.commit()
    conn.close()
    print(f"Database seeded with {len(EXPENSES_SEED)} expenses and {len(BUDGETS_SEED)} budgets.")

if __name__ == "__main__":
    seed_database()
