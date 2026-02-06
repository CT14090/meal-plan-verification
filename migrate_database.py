#!/usr/bin/env python3
"""
Database Migration Script
Adds new columns for meal type tracking
Run this ONCE after updating code
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import create_app
from database.models import db
from utils.logger import get_logger

logger = get_logger(__name__)

def run_migration():
    """Run database migration"""
    print("\n" + "="*60)
    print("DATABASE MIGRATION - MEAL TYPE TRACKING")
    print("="*60 + "\n")
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Adding breakfast_used column...")
            db.engine.execute('''
                ALTER TABLE daily_meal_usage 
                ADD COLUMN breakfast_used INTEGER DEFAULT 0
            ''')
            print("✅ Added breakfast_used")
        except Exception as e:
            if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                print("ℹ️  breakfast_used already exists")
            else:
                print(f"❌ Error adding breakfast_used: {e}")
                raise
        
        try:
            print("Adding lunch_used column...")
            db.engine.execute('''
                ALTER TABLE daily_meal_usage 
                ADD COLUMN lunch_used INTEGER DEFAULT 0
            ''')
            print("✅ Added lunch_used")
        except Exception as e:
            if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                print("ℹ️  lunch_used already exists")
            else:
                print(f"❌ Error adding lunch_used: {e}")
                raise
        
        try:
            print("Adding snack_used column...")
            db.engine.execute('''
                ALTER TABLE daily_meal_usage 
                ADD COLUMN snack_used INTEGER DEFAULT 0
            ''')
            print("✅ Added snack_used")
        except Exception as e:
            if 'already exists' in str(e) or 'duplicate' in str(e).lower():
                print("ℹ️  snack_used already exists")
            else:
                print(f"❌ Error adding snack_used: {e}")
                raise
        
        # Update any NULL values to 0
        print("\nUpdating existing records...")
        try:
            result = db.engine.execute('''
                UPDATE daily_meal_usage 
                SET breakfast_used = 0, lunch_used = 0, snack_used = 0 
                WHERE breakfast_used IS NULL OR lunch_used IS NULL OR snack_used IS NULL
            ''')
            print(f"✅ Updated {result.rowcount} existing records")
        except Exception as e:
            print(f"ℹ️  Note: {e}")
        
        print("\n" + "="*60)
        print("MIGRATION COMPLETE!")
        print("="*60)
        
        # Verify columns exist
        print("\nVerifying migration...")
        result = db.engine.execute("PRAGMA table_info(daily_meal_usage)")
        columns = [row[1] for row in result]
        
        required = ['breakfast_used', 'lunch_used', 'snack_used']
        all_present = all(col in columns for col in required)
        
        if all_present:
            print("✅ All new columns verified!")
            print("\nNew columns added:")
            for col in required:
                print(f"  - {col}")
        else:
            print("❌ Some columns missing!")
            print(f"Expected: {required}")
            print(f"Found: {columns}")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("You can now start the system with: python main.py")
        print("="*60 + "\n")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check:")
        print("1. Database file exists and is accessible")
        print("2. No other processes are using the database")
        print("3. You have write permissions")
        sys.exit(1)