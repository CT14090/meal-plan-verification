"""
Database Manager - High-level database operations
"""

from datetime import date, datetime
import pytz
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
        """Find student by RFID card UID"""
        try:
            students = Student.query.all()
            for student in students:
                try:
                    decrypted_uid = self.em.decrypt(student.card_rfid_uid)
                    if decrypted_uid == card_uid:
                        return student
                except:
                    continue
            return None
        except Exception as e:
            logger.error(f"Error finding student by RFID: {e}")
            return None
            
    def find_student_by_id(self, student_id):
        """Find student by student ID"""
        try:
            return Student.query.filter_by(student_id=student_id).first()
        except Exception as e:
            logger.error(f"Error finding student by ID: {e}")
            return None
    
    def get_all_students(self, active_only=True):
        """Get all students"""
        try:
            if active_only:
                return Student.query.filter_by(status='Active').all()
            else:
                return Student.query.all()
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
    
    def add_student(self, student_id, card_rfid_uid, student_name, grade_level,
                   meal_plan_type, daily_meal_limit, status='Active', photo_filename=None):
        """Add new student with encryption"""
        try:
            student = Student.create_encrypted(
                student_id=student_id,
                card_rfid_uid=card_rfid_uid,
                student_name=student_name,
                grade_level=grade_level,
                meal_plan_type=meal_plan_type,
                daily_meal_limit=daily_meal_limit,
                status=status,
                photo_filename=photo_filename
            )
            db.session.add(student)
            db.session.commit()
            logger.info(f"Student added: {student_id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding student: {e}")
            return None
    
    def update_student(self, student_id, **kwargs):
        """Update student information"""
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                return None
            
            if 'card_rfid_uid' in kwargs:
                student.card_rfid_uid = self.em.encrypt(kwargs['card_rfid_uid'])
            if 'student_name' in kwargs:
                student.student_name = self.em.encrypt(kwargs['student_name'])
            
            for field in ['grade_level', 'meal_plan_type', 'daily_meal_limit', 'status', 'photo_filename']:
                if field in kwargs:
                    setattr(student, field, kwargs[field])
            
            student.updated_at = datetime.utcnow()
            db.session.commit()
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating student: {e}")
            return None
    
    def delete_student(self, student_id):
        """Deactivate student"""
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                return False
            student.status = 'Inactive'
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating student: {e}")
            return False
    
    # ==================== DAILY USAGE OPERATIONS ====================
    
    def get_today_usage(self, student_id):
        """Get today's meal usage for a student"""
        try:
            today = date.today()
            usage = DailyMealUsage.query.filter_by(student_id=student_id, date=today).first()
            
            if not usage:
                usage = DailyMealUsage(
                    student_id=student_id,
                    date=today,
                    meals_used_today=0,
                    breakfast_used=0,
                    lunch_used=0,
                    snack_used=0
                )
                db.session.add(usage)
                db.session.commit()
            
            return usage
        except Exception as e:
            logger.error(f"Error getting today's usage: {e}")
            return None
    
    def auto_detect_meal_type(self):
        """Auto-detect meal type based on current time in Panama timezone"""
        try:
            panama_tz = pytz.timezone('America/Panama')
            panama_time = datetime.now(panama_tz)
            current_hour = panama_time.hour
            
            if 6 <= current_hour < 10:
                return 'Breakfast'
            elif 10 <= current_hour < 14:
                return 'Lunch'
            elif 14 <= current_hour < 17:
                return 'Snack'
            else:
                return None
        except Exception as e:
            logger.error(f"Timezone error: {e}")
            current_hour = datetime.now().hour
            if 6 <= current_hour < 10:
                return 'Breakfast'
            elif 10 <= current_hour < 14:
                return 'Lunch'
            elif 14 <= current_hour < 17:
                return 'Snack'
            else:
                return None
    
    def check_eligibility(self, student, meal_type=None):
        """Check if student is eligible for a meal"""
        try:
            # Auto-detect meal type if not provided
            if meal_type is None:
                meal_type = self.auto_detect_meal_type()
                if meal_type is None:
                    return {
                        'eligible': False,
                        'reason': 'No meals served at this time',
                        'meals_used': 0,
                        'meals_remaining': 0,
                        'meal_type_status': {},
                        'detected_meal_type': None
                    }
            
            # Check if student is active
            if student.status != 'Active':
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['INACTIVE'],
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Friday meal plan logic
            # Friday plans work Mon-Fri (all 5 days)
            # Regular plans work Mon-Thu only (NO Friday access)
            try:
                panama_tz = pytz.timezone('America/Panama')
                panama_time = datetime.now(panama_tz)
                today_weekday = panama_time.weekday()
            except:
                today_weekday = date.today().weekday()
            
            is_friday = (today_weekday == 4)
            is_friday_plan = student.meal_plan_type.startswith('Friday')
            
            # Regular plans are NOT valid on Fridays
            if not is_friday_plan and is_friday:
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['NO_FRIDAY_PLAN'],
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Check if meal type is allowed for this plan
            allowed_types = config.MEAL_PLAN_ALLOWED_TYPES.get(student.meal_plan_type, [])
            if meal_type not in allowed_types:
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['MEAL_TYPE_NOT_ALLOWED'],
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Get today's usage
            usage = self.get_today_usage(student.student_id)
            if not usage:
                return {
                    'eligible': False,
                    'reason': 'Error checking usage',
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Check if this specific meal type has already been used
            if not usage.has_meal_type_available(meal_type):
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['MEAL_TYPE_ALREADY_USED'],
                    'meals_used': usage.meals_used_today,
                    'meals_remaining': 0,
                    'meal_type_status': {
                        'breakfast_used': usage.breakfast_used,
                        'lunch_used': usage.lunch_used,
                        'snack_used': usage.snack_used
                    },
                    'detected_meal_type': meal_type
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
                    'last_meal_time': usage.last_meal_time,
                    'meal_type_status': {
                        'breakfast_used': usage.breakfast_used,
                        'lunch_used': usage.lunch_used,
                        'snack_used': usage.snack_used
                    },
                    'detected_meal_type': meal_type
                }
            
            # Student is eligible
            return {
                'eligible': True,
                'reason': None,
                'meals_used': meals_used,
                'meals_remaining': meals_remaining,
                'last_meal_time': usage.last_meal_time,
                'meal_type_status': {
                    'breakfast_used': usage.breakfast_used,
                    'lunch_used': usage.lunch_used,
                    'snack_used': usage.snack_used
                },
                'detected_meal_type': meal_type
            }
        
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return {
                'eligible': False,
                'reason': 'System error',
                'meals_used': 0,
                'meals_remaining': 0,
                'meal_type_status': {},
                'detected_meal_type': meal_type
            }
    
    def increment_meal_usage(self, student_id, meal_type=None):
        """Increment today's meal count for student"""
        try:
            if meal_type is None:
                meal_type = self.auto_detect_meal_type()
            
            usage = self.get_today_usage(student_id)
            if usage:
                usage.increment_usage(meal_type)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error incrementing meal usage: {e}")
            return False
    
    def reset_daily_usage(self):
        """Reset all daily meal usage (called at midnight)"""
        try:
            deleted = DailyMealUsage.query.delete()
            db.session.commit()
            logger.info(f"Daily usage reset complete. Deleted {deleted} records.")
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting daily usage: {e}")
            return 0
    
    # ==================== TRANSACTION OPERATIONS ====================
    
    def log_transaction(self, student_id, student_name, meal_plan_type, meal_type,
                       status, denied_reason=None):
        """Log a meal transaction"""
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
            return transaction
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging transaction: {e}")
            return None
    
    def get_recent_transactions(self, limit=50):
        """Get recent transactions"""
        try:
            return MealTransaction.query.order_by(
                MealTransaction.transaction_timestamp.desc()
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []
    
    def get_daily_stats(self):
        """Get today's transaction statistics"""
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            
            total = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start
            ).count()
            
            approved = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            denied = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_DENIED
            ).count()
            
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
            return {'total': 0, 'approved': 0, 'denied': 0, 'breakfast': 0, 'lunch': 0, 'snack': 0}
    
    # ==================== MUNDOWARE OPERATIONS ====================
    
    def update_mundoware_lookup(self, student, eligible):
        """Update MUNDOWARE shared lookup table"""
        try:
            student_name = self.em.decrypt(student.student_name)
            MundowareStudentLookup.query.filter_by(station_id=config.STATION_ID).delete()
            
            lookup = MundowareStudentLookup(
                station_id=config.STATION_ID,
                student_id=student.student_id,
                student_name=student_name,
                meal_plan_type=student.meal_plan_type,
                eligible=eligible
            )
            db.session.add(lookup)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating MUNDOWARE lookup: {e}")
            return False
    
    def clear_mundoware_lookup(self):
        """Clear MUNDOWARE lookup for this station"""
        try:
            MundowareStudentLookup.query.filter_by(station_id=config.STATION_ID).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing MUNDOWARE lookup: {e}")
            return False

_db_manager = None

def get_db_manager():
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
