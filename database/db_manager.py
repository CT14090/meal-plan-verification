"""
Database Manager - High-level database operations
Provides business logic layer on top of SQLAlchemy models
"""

from datetime import date, datetime
from sqlalchemy import and_
from config.settings import config
from config.encryption import get_encryption_manager
from database.models import db, Student, DailyMealUsage, MealTransaction, MundowareStudentLookup
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self):
        self.em = get_encryption_manager()
    
    # ==================== STUDENT OPERATIONS ====================
    
    def find_student_by_rfid(self, card_uid):
        """
        Find student by RFID card UID
        
        Args:
            card_uid: RFID card UID (plaintext)
        
        Returns:
            Student object or None
        """
        try:
            # Get all students and decrypt their card UIDs to compare
            students = Student.query.all()
            
            for student in students:
                try:
                    decrypted_uid = self.em.decrypt(student.card_rfid_uid)
                    if decrypted_uid == card_uid:
                        logger.info(f"Student found for RFID: {card_uid[:8]}***")
                        return student
                except:
                    # Skip students with invalid encrypted UIDs
                    continue
            
            logger.warning(f"No student found for RFID: {card_uid[:8]}***")
            return None
        except Exception as e:
            logger.error(f"Error finding student by RFID: {e}")
            return None
            
    def find_student_by_id(self, student_id):
        """
        Find student by student ID
        
        Args:
            student_id: Student ID (plaintext)
        
        Returns:
            Student object or None
        """
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if student:
                logger.info(f"Student found: {student_id}")
            else:
                logger.warning(f"No student found: {student_id}")
            return student
        except Exception as e:
            logger.error(f"Error finding student by ID: {e}")
            return None
    
    def get_all_students(self, active_only=True):
        """Get all students"""
        try:
            if active_only:
                students = Student.query.filter_by(status='Active').all()
            else:
                students = Student.query.all()
            return students
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
    
    def add_student(self, student_id, card_rfid_uid, student_name, grade_level,
                   meal_plan_type, daily_meal_limit, status='Active', photo_url=None):
        """
        Add new student with encryption
        
        Args:
            All student fields (plaintext)
        
        Returns:
            Student object if successful, None otherwise
        """
        try:
            student = Student.create_encrypted(
                student_id=student_id,
                card_rfid_uid=card_rfid_uid,
                student_name=student_name,
                grade_level=grade_level,
                meal_plan_type=meal_plan_type,
                daily_meal_limit=daily_meal_limit,
                status=status,
                photo_url=photo_url
            )
            
            db.session.add(student)
            db.session.commit()
            
            logger.info(f"Student added: {student_id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding student: {e}")
            return None
    
    # ==================== DAILY USAGE OPERATIONS ====================
    
    def get_today_usage(self, student_id):
        """
        Get today's meal usage for a student
        Creates new record if doesn't exist
        
        Args:
            student_id: Student ID
        
        Returns:
            DailyMealUsage object
        """
        try:
            today = date.today()
            usage = DailyMealUsage.query.filter_by(
                student_id=student_id,
                date=today
            ).first()
            
            if not usage:
                # Create new usage record for today
                usage = DailyMealUsage(
                    student_id=student_id,
                    date=today,
                    meals_used_today=0
                )
                db.session.add(usage)
                db.session.commit()
                logger.info(f"Created new daily usage record for {student_id}")
            
            return usage
        except Exception as e:
            logger.error(f"Error getting today's usage: {e}")
            return None
    
    def check_eligibility(self, student):
        """
        Check if student is eligible for a meal
        
        Args:
            student: Student object
        
        Returns:
            dict with eligibility status and details
        """
        try:
            # Check if student is active
            if student.status != 'Active':
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['INACTIVE'],
                    'meals_used': 0,
                    'meals_remaining': 0
                }
            
            # Get today's usage
            usage = self.get_today_usage(student.student_id)
            if not usage:
                return {
                    'eligible': False,
                    'reason': 'Error checking usage',
                    'meals_used': 0,
                    'meals_remaining': 0
                }
            
            # Check if under daily limit
            meals_used = usage.meals_used_today
            daily_limit = student.daily_meal_limit
            meals_remaining = max(0, daily_limit - meals_used)
            
            if meals_used >= daily_limit:
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['LIMIT_REACHED'],
                    'meals_used': meals_used,
                    'meals_remaining': 0,
                    'last_meal_time': usage.last_meal_time
                }
            
            # Student is eligible
            return {
                'eligible': True,
                'reason': None,
                'meals_used': meals_used,
                'meals_remaining': meals_remaining,
                'last_meal_time': usage.last_meal_time
            }
        
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return {
                'eligible': False,
                'reason': 'System error',
                'meals_used': 0,
                'meals_remaining': 0
            }
    
    def increment_meal_usage(self, student_id):
        """
        Increment today's meal count for student
        
        Args:
            student_id: Student ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            usage = self.get_today_usage(student_id)
            if usage:
                usage.increment_usage()
                db.session.commit()
                logger.info(f"Incremented meal usage for {student_id}: {usage.meals_used_today}")
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error incrementing meal usage: {e}")
            return False
    
    def reset_daily_usage(self):
        """
        Reset all daily meal usage (called at midnight)
        Deletes old records and creates fresh ones for active students
        
        Returns:
            Number of records reset
        """
        try:
            # Delete yesterday's records
            yesterday = date.today()
            deleted = DailyMealUsage.query.filter(DailyMealUsage.date < yesterday).delete()
            db.session.commit()
            
            logger.info(f"Daily usage reset complete. Deleted {deleted} old records.")
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting daily usage: {e}")
            return 0
    
    # ==================== TRANSACTION OPERATIONS ====================
    
    def log_transaction(self, student_id, student_name, meal_plan_type, meal_type,
                       status, denied_reason=None):
        """
        Log a meal transaction
        
        Args:
            student_id: Student ID
            student_name: Student name (plaintext - will be encrypted)
            meal_plan_type: Meal plan type
            meal_type: Breakfast, Lunch, Snack, or None
            status: Approved, Denied, Error
            denied_reason: Reason for denial (if applicable)
        
        Returns:
            MealTransaction object if successful, None otherwise
        """
        try:
            transaction = MealTransaction.create_encrypted(
                student_id=student_id,
                student_name=student_name,
                meal_plan_type=meal_plan_type,
                meal_type=meal_type,
                cashier_station=config.STATION_ID,
                cashier_id=config.CASHIER_ID,
                status=status,
                denied_reason=denied_reason
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            logger.info(f"Transaction logged: {student_id} - {status}")
            return transaction
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging transaction: {e}")
            return None
    
    def get_recent_transactions(self, limit=50):
        """Get recent transactions"""
        try:
            transactions = MealTransaction.query.order_by(
                MealTransaction.transaction_timestamp.desc()
            ).limit(limit).all()
            return transactions
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []
    
    def get_daily_stats(self):
        """Get today's transaction statistics"""
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            
            logger.info(f"Getting daily stats for {today}")
            
            # Total transactions today
            total = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start
            ).count()
            
            # Approved transactions
            approved = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            # Denied transactions
            denied = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_DENIED
            ).count()
            
            # By meal type (only approved)
            breakfast = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Breakfast',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            lunch = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Lunch',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            snack = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Snack',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            logger.info(f"Stats: total={total}, approved={approved}, denied={denied}, breakfast={breakfast}, lunch={lunch}, snack={snack}")
            
            return {
                'total': total,
                'approved': approved,
                'denied': denied,
                'breakfast': breakfast,
                'lunch': lunch,
                'snack': snack
            }
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return zeros instead of failing
            return {
                'total': 0,
                'approved': 0,
                'denied': 0,
                'breakfast': 0,
                'lunch': 0,
                'snack': 0
            }
    
    # ==================== MUNDOWARE OPERATIONS ====================
    
    def update_mundoware_lookup(self, student, eligible):
        """
        Update MUNDOWARE shared lookup table
        
        Args:
            student: Student object
            eligible: Boolean eligibility status
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Decrypt student name for MUNDOWARE (they need plaintext)
            student_name = self.em.decrypt(student.student_name)
            
            # Delete existing record for this station
            MundowareStudentLookup.query.filter_by(
                station_id=config.STATION_ID
            ).delete()
            
            # Create new record
            lookup = MundowareStudentLookup(
                station_id=config.STATION_ID,
                student_id=student.student_id,
                student_name=student_name,
                meal_plan_type=student.meal_plan_type,
                eligible=eligible
            )
            
            db.session.add(lookup)
            db.session.commit()
            
            logger.info(f"Updated MUNDOWARE lookup for station {config.STATION_ID}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating MUNDOWARE lookup: {e}")
            return False
    
    def clear_mundoware_lookup(self):
        """Clear MUNDOWARE lookup for this station"""
        try:
            MundowareStudentLookup.query.filter_by(
                station_id=config.STATION_ID
            ).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing MUNDOWARE lookup: {e}")
            return False


# Singleton instance
_db_manager = None

def get_db_manager():
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager