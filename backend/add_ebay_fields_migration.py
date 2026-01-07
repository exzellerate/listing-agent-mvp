"""
Database migration: Add eBay category and aspects fields to product_analyses table.

This migration adds two new JSON columns to store eBay-specific data:
- ebay_category: Full eBay category object with details
- ebay_aspects: eBay item specifics/aspects as key-value pairs
"""

import sqlite3
import sys

def run_migration(db_path="listing_agent.db"):
    """Add ebay_category and ebay_aspects columns to product_analyses table."""

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"Running migration on {db_path}...")

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(product_analyses)")
        columns = [row[1] for row in cursor.fetchall()]

        migrations_run = []

        # Add ebay_category column if it doesn't exist
        if 'ebay_category' not in columns:
            print("  Adding ebay_category column...")
            cursor.execute("""
                ALTER TABLE product_analyses
                ADD COLUMN ebay_category JSON
            """)
            migrations_run.append("ebay_category")
        else:
            print("  ebay_category column already exists, skipping.")

        # Add ebay_aspects column if it doesn't exist
        if 'ebay_aspects' not in columns:
            print("  Adding ebay_aspects column...")
            cursor.execute("""
                ALTER TABLE product_analyses
                ADD COLUMN ebay_aspects JSON
            """)
            migrations_run.append("ebay_aspects")
        else:
            print("  ebay_aspects column already exists, skipping.")

        # Commit changes
        if migrations_run:
            conn.commit()
            print(f"\n✅ Migration completed successfully!")
            print(f"   Added columns: {', '.join(migrations_run)}")
        else:
            print("\n✅ No migrations needed - all columns already exist.")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "listing_agent.db"
    success = run_migration(db_path)
    sys.exit(0 if success else 1)
