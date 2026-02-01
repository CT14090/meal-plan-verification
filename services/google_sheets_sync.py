"""
Google Sheets Sync Service - Sends transaction data to Google Sheets
Uses Google Apps Script Web App as the endpoint
"""

import requests
from datetime import datetime
from config.settings import config
from utils.logger import get_logger

logger = get_logger(__name__)

class GoogleSheetsService:
    """Manages Google Sheets synchronization"""
    
    def __init__(self):
        self.web_app_url = config.GOOGLE_SHEETS_WEB_APP_URL
        self.enabled = config.GOOGLE_SHEETS_ENABLED
    
    def log_transaction(self, student_id, meal_type, status):
        """
        Log transaction to Google Sheets immediately
        
        Args:
            student_id: Student ID
            meal_type: Breakfast, Lunch, Snack
            status: Approved or Denied
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Google Sheets sync disabled")
            return False
        
        try:
            now = datetime.now()
            
            # Format date and time (no seconds in time)
            day = now.strftime('%Y-%m-%d')
            time = now.strftime('%I:%M %p')  # e.g., "08:15 AM"
            
            # Prepare data
            payload = {
                'action': 'log_transaction',
                'day': day,
                'time': time,
                'student_id': student_id,
                'meal_type': meal_type or 'Unknown',
                'status': status
            }
            
            # Send to Google Apps Script
            response = requests.post(
                self.web_app_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    logger.info(f"✅ Logged to Google Sheets: {student_id} - {meal_type} - {status}")
                    return True
                else:
                    logger.warning(f"Google Sheets returned error: {result.get('message')}")
                    return False
            else:
                logger.warning(f"Google Sheets HTTP error: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error logging to Google Sheets: {e}")
            return False
    
    def log_daily_summary(self, date, breakfast_count, lunch_count, snacks_count):
        """
        Log daily summary to Google Sheets (called at 2pm)
        Only counts APPROVED transactions
        
        Args:
            date: Date string (YYYY-MM-DD)
            breakfast_count: Number of approved breakfasts
            lunch_count: Number of approved lunches
            snacks_count: Number of approved snacks
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Google Sheets sync disabled")
            return False
        
        try:
            # Prepare data
            payload = {
                'action': 'daily_summary',
                'date': date,
                'breakfast': breakfast_count,
                'lunch': lunch_count,
                'snacks': snacks_count
            }
            
            # Send to Google Apps Script
            response = requests.post(
                self.web_app_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    total = breakfast_count + lunch_count + snacks_count
                    logger.info(f"✅ Daily summary logged to Google Sheets: {date} - Total: {total}")
                    print(f"📊 Daily summary sent to Google Sheets: {breakfast_count} breakfast, {lunch_count} lunch, {snacks_count} snacks")
                    return True
                else:
                    logger.warning(f"Google Sheets returned error: {result.get('message')}")
                    return False
            else:
                logger.warning(f"Google Sheets HTTP error: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Error logging daily summary to Google Sheets: {e}")
            return False


# Singleton instance
_sheets_service = None

def get_sheets_service():
    """Get or create Google Sheets service singleton"""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service
