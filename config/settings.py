"""
Settings Module - Centralized configuration management
Loads environment variables and provides application-wide settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Database Configuration
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'meal_plan.db')
    
    # MySQL Configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'meal_plan_user')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'meal_plan_db')
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        """Generate SQLAlchemy database URI based on type"""
        if self.DATABASE_TYPE == 'mysql':
            return (
                f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            )
        else:  # SQLite
            return f"sqlite:///{self.DATABASE_PATH}"
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # SQLAlchemy Settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Disable SQL query logging in terminal
    
    # Station Configuration
    STATION_ID = os.getenv('STATION_ID', 'Station_1')
    CASHIER_ID = os.getenv('CASHIER_ID', 'CASHIER_01')
    
    # RFID Reader Configuration
    RFID_ENABLED = os.getenv('RFID_ENABLED', 'True').lower() == 'true'
    RFID_TIMEOUT = int(os.getenv('RFID_TIMEOUT', 5))
    
    # MUNDOWARE Integration
    MUNDOWARE_ENABLED = os.getenv('MUNDOWARE_ENABLED', 'True').lower() == 'true'
    MUNDOWARE_SHARED_TABLE = os.getenv('MUNDOWARE_SHARED_TABLE', 'mundoware_student_lookup')
    MUNDOWARE_HOST = os.getenv('MUNDOWARE_HOST', 'localhost')
    MUNDOWARE_PORT = int(os.getenv('MUNDOWARE_PORT', 3306))
    MUNDOWARE_USER = os.getenv('MUNDOWARE_USER', 'mundoware_user')
    MUNDOWARE_PASSWORD = os.getenv('MUNDOWARE_PASSWORD', '')
    MUNDOWARE_DATABASE = os.getenv('MUNDOWARE_DATABASE', 'mundoware_db')
    
    @property
    def MUNDOWARE_CONNECTION_STRING(self):
        """Generate MUNDOWARE database connection string"""
        return (
            f"mysql+pymysql://{self.MUNDOWARE_USER}:{self.MUNDOWARE_PASSWORD}"
            f"@{self.MUNDOWARE_HOST}:{self.MUNDOWARE_PORT}/{self.MUNDOWARE_DATABASE}"
        )
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'logs/')
    LOG_RETENTION_DAYS = int(os.getenv('LOG_RETENTION_DAYS', 30))
    
    # UI Configuration
    TOUCHSCREEN_AUTO_RESET_SECONDS = int(os.getenv('TOUCHSCREEN_AUTO_RESET_SECONDS', 3))
    TOUCHSCREEN_FULLSCREEN = os.getenv('TOUCHSCREEN_FULLSCREEN', 'True').lower() == 'true'
    
    # Scheduler Configuration
    DAILY_RESET_TIME = os.getenv('DAILY_RESET_TIME', '00:00')
    
    # Encryption
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    # Business Rules
    MEAL_PLAN_TYPES = {
        'Basic': 1,      # 1 meal per day
        'Premium': 2,    # 2 meals per day
        'Unlimited': 999 # Unlimited meals
    }
    
    MEAL_TYPES = ['Breakfast', 'Lunch', 'Snack']
    
    # Transaction Statuses
    STATUS_APPROVED = 'Approved'
    STATUS_DENIED = 'Denied'
    STATUS_ERROR = 'Error'
    
    # Denial Reasons
    DENIAL_REASONS = {
        'LIMIT_REACHED': 'Daily meal limit reached',
        'NO_PLAN': 'No active meal plan found',
        'CARD_NOT_FOUND': 'Card not recognized',
        'INACTIVE': 'Student account inactive',
        'MANUAL_OVERRIDE': 'Manually denied by cashier'
    }
    
    def validate(self):
        """Validate critical configuration settings"""
        errors = []
        
        # Check encryption key
        if not self.ENCRYPTION_KEY:
            errors.append("ENCRYPTION_KEY is not set in environment variables")
        
        # Check database configuration
        if self.DATABASE_TYPE not in ['sqlite', 'mysql']:
            errors.append(f"Invalid DATABASE_TYPE: {self.DATABASE_TYPE}")
        
        if self.DATABASE_TYPE == 'mysql' and not self.MYSQL_PASSWORD:
            errors.append("MYSQL_PASSWORD is required for MySQL database")
        
        # Check station ID
        if not self.STATION_ID:
            errors.append("STATION_ID is not set")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
        
        return True


# Singleton instance
config = Config()


if __name__ == "__main__":
    # Test configuration
    print("=== Meal Plan Verification System Configuration ===\n")
    
    print(f"Database Type: {config.DATABASE_TYPE}")
    print(f"Database URI: {config.SQLALCHEMY_DATABASE_URI}")
    print(f"\nStation ID: {config.STATION_ID}")
    print(f"Cashier ID: {config.CASHIER_ID}")
    print(f"\nRFID Enabled: {config.RFID_ENABLED}")
    print(f"MUNDOWARE Enabled: {config.MUNDOWARE_ENABLED}")
    print(f"\nFlask Host: {config.FLASK_HOST}:{config.FLASK_PORT}")
    print(f"Debug Mode: {config.FLASK_DEBUG}")
    
    print(f"\nMeal Plan Types: {config.MEAL_PLAN_TYPES}")
    print(f"Meal Types: {config.MEAL_TYPES}")
    
    print("\nValidating configuration...")
    try:
        config.validate()
        print("✅ Configuration valid!")
    except ValueError as e:
        print(f"❌ Configuration errors:\n{e}")