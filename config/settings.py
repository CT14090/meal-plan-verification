"""
Settings Module - Centralized configuration management
"""

import os
from dotenv import load_dotenv

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
            return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        else:
            return f"sqlite:///{self.DATABASE_PATH}"
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # SQLAlchemy Settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Station Configuration
    STATION_ID = os.getenv('STATION_ID', 'Station_1')
    CASHIER_ID = os.getenv('CASHIER_ID', 'CASHIER_01')
    
    # RFID Reader Configuration
    RFID_ENABLED = os.getenv('RFID_ENABLED', 'True').lower() == 'true'
    
    # MUNDOWARE Integration
    MUNDOWARE_ENABLED = os.getenv('MUNDOWARE_ENABLED', 'True').lower() == 'true'
    
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
    
    # Meal Plan Types
    MEAL_PLAN_TYPES = {
        'Basic': 1,
        'Plus': 2,
        'Premium': 3,
        'Unlimited': 999,
        'FridayBasic': 1,
        'FridayPlus': 2,
        'FridayPremium': 3,
    }
    
    # Meal type restrictions by plan
    MEAL_PLAN_ALLOWED_TYPES = {
        'Basic': ['Lunch'],
        'Plus': ['Lunch', 'Snack'],
        'Premium': ['Breakfast', 'Lunch', 'Snack'],
        'Unlimited': ['Breakfast', 'Lunch', 'Snack'],
        'FridayBasic': ['Lunch'],
        'FridayPlus': ['Lunch', 'Snack'],
        'FridayPremium': ['Breakfast', 'Lunch', 'Snack'],
    }
    
    MEAL_TYPES = ['Breakfast', 'Lunch', 'Snack']
    
    # Transaction Statuses
    STATUS_APPROVED = 'Approved'
    STATUS_DENIED = 'Denied'
    STATUS_ERROR = 'Error'
    
    # Denial Reasons
    DENIAL_REASONS = {
        'LIMIT_REACHED': 'Daily meal limit reached',
        'MEAL_TYPE_NOT_ALLOWED': 'This meal type is not included in your plan',
        'MEAL_TYPE_ALREADY_USED': 'You already used this meal type today',
        'NO_FRIDAY_PLAN': 'Regular meal plans not valid on Fridays',
        'CARD_NOT_FOUND': 'Card not recognized',
        'INACTIVE': 'Student account inactive',
        'MANUAL_OVERRIDE': 'Manually denied by cashier'
    }
    
    # Google Sheets Integration
    GOOGLE_SHEETS_ENABLED = os.getenv('GOOGLE_SHEETS_ENABLED', 'False').lower() == 'true'
    GOOGLE_SHEETS_WEB_APP_URL = os.getenv('GOOGLE_SHEETS_WEB_APP_URL', '')
    
    # Photo storage
    PHOTO_UPLOAD_FOLDER = 'web/static/photos'
    ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_PHOTO_SIZE_MB = 5
    
    def validate(self):
        """Validate critical configuration settings"""
        errors = []
        
        if not self.ENCRYPTION_KEY:
            errors.append("ENCRYPTION_KEY is not set in environment variables")
        
        if self.DATABASE_TYPE not in ['sqlite', 'mysql']:
            errors.append(f"Invalid DATABASE_TYPE: {self.DATABASE_TYPE}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
        
        return True

config = Config()
